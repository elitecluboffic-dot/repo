export async function onRequest(context) {
  const clientId = context.env.DISCORD_CLIENT_ID;
  const redirectUri = "https://qqq-streaming.pages.dev/api/auth/callback";
  const scope = "identify guilds.members.read";
  const url = `https://discord.com/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}`;
  return Response.redirect(url, 302);
}
