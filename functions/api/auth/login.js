const BASE_URL = "https://qqq-streaming.pages.dev";

export async function onRequest(context) {
  const clientId = context.env.DISCORD_CLIENT_ID;

  // Guard: pastikan client ID ada
  if (!clientId) {
    console.error("DISCORD_CLIENT_ID is not set");
    return new Response(
      `<!DOCTYPE html><html><head><meta charset="UTF-8">
      <style>
        body { font-family: monospace; background: #080810; color: #f0f0f5;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0; }
        .box { background: #13131f; border: 1px solid #e63946; border-radius: 12px;
               padding: 32px 40px; max-width: 480px; text-align: center; }
        h2 { color: #e63946; margin-bottom: 12px; }
        p  { color: #6b6b8a; font-size: 13px; line-height: 1.6; }
        code { background: #1e1e30; padding: 2px 8px; border-radius: 4px; color: #ffd166; }
        a { color: #5865F2; }
      </style></head><body>
      <div class="box">
        <h2>⚠️ Konfigurasi Error</h2>
        <p>Environment variable <code>DISCORD_CLIENT_ID</code> tidak ditemukan.</p>
        <p style="margin-top:16px">Set di <a href="https://dash.cloudflare.com" target="_blank">
        Cloudflare Dashboard</a> → Pages → Settings → Environment Variables, lalu redeploy.</p>
      </div></body></html>`,
      { status: 500, headers: { "Content-Type": "text/html" } }
    );
  }

  // Cek cookie — kalau sudah ada session yang valid, langsung redirect ke home
  // (mencegah spam login yang trigger rate limit Discord)
  const cookie = context.request.headers.get("Cookie") || "";
  if (cookie.includes("session=")) {
    return Response.redirect(`${BASE_URL}/`, 302);
  }

  const redirectUri = `${BASE_URL}/api/auth/callback`;
  const scope       = "identify guilds.members.read";
  const state       = crypto.randomUUID();

  const url = `https://discord.com/oauth2/authorize` +
    `?client_id=${clientId}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_type=code` +
    `&scope=${encodeURIComponent(scope)}` +
    `&state=${state}` +
    `&prompt=none`; // skip consent screen kalau sudah pernah authorize

  return new Response(null, {
    status: 302,
    headers: {
      "Location":   url,
      "Set-Cookie": `oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=300`
    }
  });
}
