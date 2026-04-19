export async function onRequest() {
  return new Response(null, {
    status: 302,
    headers: {
      Location: "/",
      "Set-Cookie": "session=; Path=/; HttpOnly; Secure; Max-Age=0"
    }
  });
}
