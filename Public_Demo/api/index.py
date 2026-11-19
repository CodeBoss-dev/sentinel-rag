"""Public, serverless version of the Sentinel-RAG dashboard (Vercel).

Everything the dashboard shows comes from the team's saved runs, and the scratch-trained
classifier runs live (NumPy). Live three-assistant questions need the local Ollama models,
so this public copy explains that instead of answering them.
"""
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from numpy_model import classify_text, explain_text  # noqa: E402

root = Path(__file__).resolve().parent.parent
data_folder = root / "data"
app = Flask(__name__, template_folder=str(root / "templates"), static_folder=str(root / "static"))
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


class RestoreOriginalPath:
    """Vercel rewrites every request to /api/index?__path=/<original>; put the original path back."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        from urllib.parse import parse_qsl, urlencode
        if environ.get("PATH_INFO", "").startswith("/api/index"):
            pairs = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
            original = next((v for k, v in pairs if k == "__path"), None)
            if original is not None:
                environ["PATH_INFO"] = original or "/"
                environ["QUERY_STRING"] = urlencode([(k, v) for k, v in pairs if k != "__path"])
        return self.wsgi_app(environ, start_response)


app.wsgi_app = RestoreOriginalPath(app.wsgi_app)
max_characters = 10000


def read_query(limit=max_characters):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="Send a JSON object containing query."), 400)
    query = data.get("query")
    if not isinstance(query, str) or not query.strip():
        return None, (jsonify(error="Enter some text first."), 400)
    if len(query) > limit:
        return None, (jsonify(error=f"Use no more than {limit:,} characters."), 400)
    return query.strip(), None


def saved(name):
    return app.response_class((data_folder / name).read_text(), mimetype="application/json")


@app.get("/")
def home():
    return render_template("index.html", max_characters=max_characters)


@app.post("/api/classify")
def classify():
    query, error = read_query()
    return error or jsonify(classify_text(query))


@app.post("/api/explain")
def explain():
    query, error = read_query()
    return error or jsonify(explain_text(query))


@app.post("/api/ask")
def ask():
    return jsonify(error="Asking a new question needs the two local AI models (Llama 3.2 and Gemma 2), which run "
                         "on the team's own computer. This public demo replays the saved test runs, so please pick "
                         "one of the ready-made questions."), 503


@app.get("/api/suite")
def suite():
    return saved("suite_results.json")


@app.get("/api/industries")
def industries():
    return saved("industry_results.json")


@app.get("/api/model")
def model_report():
    return saved("model_report.json")


@app.get("/api/config")
def config():
    return saved("config.json")


@app.get("/api/corpus")
def corpus():
    return saved("corpus.json")


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="The text is too large. Use no more than 10,000 characters."), 413


@app.errorhandler(500)
def server_error(error):
    return jsonify(error="Something went wrong. Please try again."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
