// ─── Base64URL decode helper ───
function fromB64Url(str) {
  const base64 = str
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(str.length + (4 - (str.length % 4)) % 4, "=");
  return atob(base64);
}

// ─── JWT Generator (Base64URL safe) ───
async function generateJWT(payload, secret) {
  const toB64Url = (str) =>
    btoa(unescape(encodeURIComponent(str)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");

  const header = toB64Url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body   = toB64Url(JSON.stringify(payload));
  const data   = `${header}.${body}`;

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sig    = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

  return `${data}.${sigB64}`;
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

    const sigBytes = Uint8Array.from(fromB64Url(sig), c => c.charCodeAt(0));
    const valid    = await crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(data));
    if (!valid) return null;

    const parsed = JSON.parse(fromB64Url(payload));
    if (parsed.exp < Math.floor(Date.now() / 1000)) return { ...parsed, expired: true };

    return parsed;
  } catch (err) {
    console.error("JWT verify error:", err);
    return null;
  }
}

// ─── Refresh Discord Token ───
async function refreshDiscordToken(refreshToken, clientId, clientSecret) {
  try {
    const res = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id:     clientId,
        client_secret: clientSecret,
        grant_type:    "refresh_token",
        refresh_token: refreshToken
      })
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.access_token) return null;
    return data;
  } catch {
    return null;
  }
}

// ─── Movies Handler ───
export async function onRequest(context) {
  const cookie       = context.request.headers.get("Cookie") || "";
  const sessionMatch = cookie.match(/session=([^;]+)/);

  if (!sessionMatch) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  const jwtSecret    = context.env.JWT_SECRET;
  const clientId     = context.env.DISCORD_CLIENT_ID;
  const clientSecret = context.env.DISCORD_CLIENT_SECRET;

  if (!jwtSecret) {
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  let user = await verifyJWT(sessionMatch[1], jwtSecret);

  // JWT tidak valid sama sekali
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": "session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
      }
    });
  }

  // JWT expired tapi ada refresh_token → coba auto-renew
  let newCookieHeader = null;
  if (user.expired && user.refresh_token && clientId && clientSecret) {
    console.log("JWT expired, attempting refresh for:", user.username);
    const refreshed = await refreshDiscordToken(user.refresh_token, clientId, clientSecret);

    if (refreshed) {
      // Buat JWT baru dengan token baru
      const newJwt = await generateJWT({
        id:            user.id,
        username:      user.username,
        avatar:        user.avatar,
        nick:          user.nick,
        refresh_token: refreshed.refresh_token,
        exp:           Math.floor(Date.now() / 1000) + 604800 // 7 hari lagi
      }, jwtSecret);

      newCookieHeader = `session=${newJwt}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`;
      console.log("Session refreshed for:", user.username);
    } else {
      // Refresh token sudah tidak valid → minta login ulang
      console.log("Refresh failed, clearing session");
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
          "Set-Cookie": "session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
        }
      });
    }
  }

  // Fetch data film
  const API_URL = context.env.MOVIES_API_URL;
  if (!API_URL) {
    return new Response(JSON.stringify({ error: "Server config error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const res  = await fetch(API_URL + "?t=" + Date.now());
    if (!res.ok) throw new Error(`Upstream error: ${res.status}`);
    const data = await res.json();

    const headers = {
      "Content-Type":                "application/json",
      "Cache-Control":               "no-store",
      "Access-Control-Allow-Origin": "*"
    };

    // Kalau session di-renew, kirim cookie baru ke browser
    if (newCookieHeader) headers["Set-Cookie"] = newCookieHeader;

    return new Response(JSON.stringify(data), { headers });

  } catch (err) {
    console.error("Movies fetch error:", err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}