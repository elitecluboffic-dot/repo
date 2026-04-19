export async function onRequest(context) {
  const API_URL = context.env.MOVIES_API_URL;
  
  const res = await fetch(API_URL + "?t=" + Date.now());
  const data = await res.json();
  
  return new Response(JSON.stringify(data), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    }
  });
}
