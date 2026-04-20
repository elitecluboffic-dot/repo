// ─── Base64URL decode helper ───
function fromB64Url(str) {
  // Ganti Base64URL chars ke Base64 standar, lalu tambah padding
  const base64 = str
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(str.length + (4 - (str.length % 4)) % 4, "=");
  return atob(base64);
}

// ─── JWT Verifier (Base64URL safe) ───
async function verifyJWT(token, secret) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const [header, payload, sig] = parts;
    const data = `${header}.${payload}`;

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"]
    );

    // Decode Base64URL signature → bytes
    const sigBytes = Uint8Array.from(fromB64Url(sig), c => c.charCodeAt(0));

    const valid = await crypto.subtle.verify(
      "HMAC", key, sigBytes, new TextEncoder().encode(data)
    );
    if (!valid) return null;

    // Decode payload
    const parsed = JSON.parse(fromB64Url(payload));

    // Cek expiry
    if (parsed.exp < Math.floor(Date.now() / 1000)) return null;

    return parsed;
  } catch (err) {
    console.error("JWT verify error:", err);
    return null;
  }
}

// ─── Movies Handler ───
export async function onRequest(context) {
  // 1. Ambil session cookie
  const cookie       = context.request.headers.get("Cookie") || "";
  const sessionMatch = cookie.match(/session=([^;]+)/);

  if (!sessionMatch) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  // 2. Verifikasi JWT
  const jwtSecret = context.env.JWT_SECRET;
  if (!jwtSecret) {
    console.error("JWT_SECRET is not set");
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  const user = await verifyJWT(sessionMatch[1], jwtSecret);
  if (!user) {
    // Clear cookie yang invalid/expired
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": "session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
      }
    });
  }

  // 3. Fetch data film
  const API_URL = context.env.MOVIES_API_URL;
  if (!API_URL) {
    console.error("MOVIES_API_URL is not set");
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
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
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}
