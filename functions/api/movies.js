function fromB64Url(str) {
  return atob(str.replace(/-/g, "+").replace(/_/g, "/")
    .padEnd(str.length + (4 - str.length % 4) % 4, "="));
}

async function verifyJWT(token, secret) {
  try {
    const [header, payload, sig] = token.split(".");
    if (!header || !payload || !sig) return null;
    const data = `${header}.${payload}`;
    const key = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" }, false, ["verify"]
    );
    const sigBytes = Uint8Array.from(fromB64Url(sig), c => c.charCodeAt(0));
    const valid = await crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(data));
    if (!valid) return null;
    const parsed = JSON.parse(fromB64Url(payload));
    if (parsed.exp < Math.floor(Date.now() / 1000)) return null;
    return parsed;
  } catch (err) {
    console.error("JWT verify error:", err);
    return null;
  }
}

export async function onRequest(context) {
  const cookie       = context.request.headers.get("Cookie") || "";
  const sessionMatch = cookie.match(/session=([^;]+)/);

  if (!sessionMatch) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401, headers: { "Content-Type": "application/json" }
    });
  }

  const jwtSecret = context.env.JWT_SECRET;
  if (!jwtSecret) {
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500, headers: { "Content-Type": "application/json" }
    });
  }

  const user = await verifyJWT(sessionMatch[1], jwtSecret);
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": "session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
      }
    });
  }

  const API_URL = context.env.MOVIES_API_URL;
  if (!API_URL) {
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500, headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const res  = await fetch(API_URL + "?t=" + Date.now());
    if (!res.ok) throw new Error(`Upstream error: ${res.status}`);
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      headers: {
        "Content-Type":                "application/json",
        "Cache-Control":               "no-store",
        "Access-Control-Allow-Origin": "*"
      }
    });
  } catch (err) {
    console.error("Movies fetch error:", err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500, headers: { "Content-Type": "application/json" }
    });
  }
}