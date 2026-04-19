export async function onRequest(context) {
  const clientId = context.env.DISCORD_CLIENT_ID;
  const redirectUri = "https://qqq-streaming.pages.dev/api/auth/callback";
  const scope = "identify guilds.members.read";
  
  // Generate random state untuk CSRF protection
  const state = crypto.randomUUID();
  
  const url = `https://discord.com/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&state=${state}`;
  
  const response = Response.redirect(url, 302);
  
  // Simpan state di cookie untuk diverifikasi di callback
  return new Response(null, {
    status: 302,
    headers: {
      Location: url,
      "Set-Cookie": `oauth_state=${state}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=300`
    }
  });
}
