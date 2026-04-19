async function generateJWT(payload, secret) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  const data = `${header}.${body}`;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return `${data}.${sigB64}`;
}

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const code = url.searchParams.get("code");
  if (!code) return Response.redirect("/?error=no_code", 302);

  const clientId = context.env.DISCORD_CLIENT_ID;
  const clientSecret = context.env.DISCORD_CLIENT_SECRET;
  const redirectUri = "https://qqq-streaming.pages.dev/api/auth/callback";
  const guildId = context.env.DISCORD_GUILD_ID;
  const jwtSecret = context.env.JWT_SECRET;

  try {
    // Tukar code jadi token
    const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        grant_type: "authorization_code",
        code,
        redirect_uri: redirectUri
      })
    });
    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) return Response.redirect("/?error=token_failed", 302);

    // Ambil info user
    const userRes = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokenData.access_token}` }
    });
    const user = await userRes.json();

    // Cek user ada di guild
    const memberRes = await fetch(`https://discord.com/api/users/@me/guilds/${guildId}/member`, {
      headers: { Authorization: `Bearer ${tokenData.access_token}` }
    });
    if (!memberRes.ok) return Response.redirect("/?error=not_member", 302);

    // Buat JWT session
    const jwt = await generateJWT({
      id: user.id,
      username: user.username,
      exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 // 24 jam
    }, jwtSecret);

    // Set cookie dan redirect ke home
    return new Response(null, {
      status: 302,
      headers: {
        Location: "/",
        "Set-Cookie": `session=${jwt}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=86400`
      }
    });
  } catch (err) {
    return Response.redirect("/?error=server_error", 302);
  }
}
