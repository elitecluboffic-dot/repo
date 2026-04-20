// functions/api/auth/[action].js
// Handles: /api/auth/login, /api/auth/register, /api/auth/logout

const BASE_URL = "https://qqq-streaming.pages.dev";

// ─── Helpers ───
async function hashPassword(password) {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(password)
  );
  return btoa(String.fromCharCode(...new Uint8Array(buf)));
}

const toB64Url = (str) =>
  btoa(unescape(encodeURIComponent(str)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function generateJWT(payload, secret) {
  const header = toB64Url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body   = toB64Url(JSON.stringify(payload));
  const data   = `${header}.${body}`;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${data}.${sigB64}`;
}

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
  } catch { return null; }
}

function jsonRes(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...extraHeaders }
  });
}

// ─── Main Handler ───
export async function onRequest(context) {
  const { params, request, env } = context;
  const action = params.action;
  const method = request.method;

  // CORS preflight
  if (method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": BASE_URL,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
      }
    });
  }

  const KV        = env.USERS_KV;   // Cloudflare KV namespace
  const jwtSecret = env.JWT_SECRET;

  if (!KV || !jwtSecret) {
    return jsonRes({ error: "Server config error" }, 500);
  }

  // ─── REGISTER ───
  if (action === "register" && method === "POST") {
    let body;
    try { body = await request.json(); } catch { return jsonRes({ error: "Invalid JSON" }, 400); }

    const { username, password } = body;
    if (!username || !password)
      return jsonRes({ error: "Username dan password wajib diisi" }, 400);
    if (username.length < 3 || username.length > 20)
      return jsonRes({ error: "Username harus 3-20 karakter" }, 400);
    if (password.length < 6)
      return jsonRes({ error: "Password minimal 6 karakter" }, 400);
    if (!/^[a-zA-Z0-9_]+$/.test(username))
      return jsonRes({ error: "Username hanya boleh huruf, angka, dan underscore" }, 400);

    // Cek apakah username sudah ada
    const existing = await KV.get(`user:${username.toLowerCase()}`);
    if (existing) return jsonRes({ error: "Username sudah dipakai" }, 409);

    // Simpan user
    const hashed = await hashPassword(password);
    await KV.put(`user:${username.toLowerCase()}`, JSON.stringify({
      username,
      password: hashed,
      created_at: new Date().toISOString()
    }));

    // Auto-login setelah register
    const jwt = await generateJWT({
      id:       username.toLowerCase(),
      username,
      exp:      Math.floor(Date.now() / 1000) + 604800
    }, jwtSecret);

    return jsonRes({ ok: true, username }, 200, {
      "Set-Cookie": `session=${jwt}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`
    });
  }

  // ─── LOGIN ───
  if (action === "login" && method === "POST") {
    let body;
    try { body = await request.json(); } catch { return jsonRes({ error: "Invalid JSON" }, 400); }

    const { username, password } = body;
    if (!username || !password)
      return jsonRes({ error: "Username dan password wajib diisi" }, 400);

    const raw = await KV.get(`user:${username.toLowerCase()}`);
    if (!raw) return jsonRes({ error: "Username atau password salah" }, 401);

    const user   = JSON.parse(raw);
    const hashed = await hashPassword(password);
    if (hashed !== user.password)
      return jsonRes({ error: "Username atau password salah" }, 401);

    const jwt = await generateJWT({
      id:       username.toLowerCase(),
      username: user.username,
      exp:      Math.floor(Date.now() / 1000) + 604800
    }, jwtSecret);

    return jsonRes({ ok: true, username: user.username }, 200, {
      "Set-Cookie": `session=${jwt}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`
    });
  }

  // ─── LOGOUT ───
  if (action === "logout") {
    return new Response(null, {
      status: 302,
      headers: {
        "Location":   `${BASE_URL}/`,
        "Set-Cookie": "session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0"
      }
    });
  }

  // ─── CHECK SESSION ───
  if (action === "me" && method === "GET") {
    const cookie = request.headers.get("Cookie") || "";
    const match  = cookie.match(/session=([^;]+)/);
    if (!match) return jsonRes({ error: "Unauthorized" }, 401);
    const user = await verifyJWT(match[1], jwtSecret);
    if (!user) return jsonRes({ error: "Unauthorized" }, 401);
    return jsonRes({ ok: true, username: user.username });
  }

  return jsonRes({ error: "Not found" }, 404);
}