const BASE_URL = "https://qqq-streaming.pages.dev";

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

// ─── Callback Handler ───
export async function onRequest(context) {
  const url  = new URL(context.request.url);
  const code = url.searchParams.get("code");

  if (!code) return Response.redirect(`${BASE_URL}/?error=no_code`, 302);

  const clientId     = context.env.DISCORD_CLIENT_ID;
  const clientSecret = context.env.DISCORD_CLIENT_SECRET;
  const redirectUri  = `${BASE_URL}/api/auth/callback`;
  const guildId      = context.env.DISCORD_GUILD_ID;
  const jwtSecret    = context.env.JWT_SECRET;

  if (!clientId || !clientSecret || !guildId || !jwtSecret) {
    console.error("Missing env vars");
    return Response.redirect(`${BASE_URL}/?error=config_error`, 302);
  }

  try {
    // 1. Tukar code → access token
    const tokenRes  = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id:     clientId,
        client_secret: clientSecret,
        grant_type:    "authorization_code",
        code,
        redirect_uri:  redirectUri
      })
    });

    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      console.error("Token exchange failed:", tokenData);
      return Response.redirect(`${BASE_URL}/?error=token_failed`, 302);
    }

    // 2. Ambil info user
    const userRes = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokenData.access_token}` }
    });
    if (!userRes.ok) {
      console.error("User fetch failed:", userRes.status);
      return Response.redirect(`${BASE_URL}/?error=user_fetch_failed`, 302);
    }
    const user = await userRes.json();

    // 3. Cek membership di guild
    const memberRes = await fetch(
      `https://discord.com/api/users/@me/guilds/${guildId}/member`,
      { headers: { Authorization: `Bearer ${tokenData.access_token}` } }
    );
    if (!memberRes.ok) {
      console.error("Guild check failed:", memberRes.status, "user:", user.username);
      return Response.redirect(`${BASE_URL}/?error=not_member`, 302);
    }
    const member = await memberRes.json();

    // 4. Buat JWT
    const jwt = await generateJWT({
      id:       user.id,
      username: user.username,
      avatar:   user.avatar,
      nick:     member.nick || user.global_name || user.username,
      exp:      Math.floor(Date.now() / 1000) + 86400
    }, jwtSecret);

    // 5. Set cookie & redirect
    return new Response(null, {
      status: 302,
      headers: {
        "Location":   `${BASE_URL}/`,
        "Set-Cookie": `session=${jwt}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=86400`
      }
    });

  } catch (err) {
    console.error("Callback error:", err);
    return Response.redirect(`${BASE_URL}/?error=server_error`, 302);
  }
}
