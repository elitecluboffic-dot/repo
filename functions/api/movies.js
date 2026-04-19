export async function onRequest(context) {
  const token = context.request.headers.get("X-API-Token") || "";
  const secret = context.env.API_SECRET || "";

  if (token !== secret) {
    return new Response(JSON.stringify({ 
      error: "Forbidden",
      debug_token: token,
      debug_secret: secret,
      debug_match: token === secret
    }), {
      status: 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  const API_URL = context.env.MOVIES_API_URL;
  if (!API_URL) {
    return new Response(JSON.stringify({ error: "MOVIES_API_URL tidak ada" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
  try {
    const res = await fetch(API_URL + "?t=" + Date.now());
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}
