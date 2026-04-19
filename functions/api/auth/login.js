export async function onRequest(context) {
  const clientId = context.env.DISCORD_CLIENT_ID || "TIDAK ADA";

  return new Response(JSON.stringify({
    client_id: clientId
  }), {
    headers: { "Content-Type": "application/json" }
  });
}
