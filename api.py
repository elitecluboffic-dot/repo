from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

JSON_FILE = "movies.json"
LINKS_FILE = "direct_links.txt"

def load_movies():
    if not os.path.exists(JSON_FILE):
        return [], ""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("movies", []), data.get("last_updated", "")

@app.route("/api/movies")
def get_movies():
    page   = int(request.args.get("page", 1))
    limit  = int(request.args.get("limit", 50))
    search = request.args.get("q", "").strip().lower()

    movies, last_updated = load_movies()

    if search:
        movies = [m for m in movies if search in m.get("title", "").lower()]

    total  = len(movies)
    offset = (page - 1) * limit
    paged  = movies[offset:offset + limit]

    return jsonify({
        "total": total,
        "page": page,
        "limit": limit,
        "last_updated": last_updated,
        "movies": paged
    })

@app.route("/api/stats")
def stats():
    movies, last_updated = load_movies()
    return jsonify({
        "total": len(movies),
        "last_updated": last_updated
    })

@app.route("/api/links")
def get_links():
    if not os.path.exists(LINKS_FILE):
        return jsonify({"error": "direct_links.txt tidak ditemukan"}), 404
    links = []
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and "](" in line:
                title = line[1:line.index("](")]
                url   = line[line.index("](")+2:-1]
                links.append({"title": title, "url": url})
    return jsonify({
        "total": len(links),
        "links": links
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)