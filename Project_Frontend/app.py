import csv
import json
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from inference import architecture, classify_text, explain_text, test_set_report


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
max_characters = 10000
folder = Path(__file__).parent
data_folder = folder / "data"

# The full three-system engine (embeddings + Ollama) loads only when a live question is asked.
engine = None
engine_lock = threading.Lock()


def get_engine():
    global engine
    with engine_lock:
        if engine is None:
            from sentinel import Sentinel, documents_folder
            # Live questions search the evaluated documents plus the extended knowledge base.
            # The saved test suite and every reported number use only the evaluated documents.
            files = sorted(documents_folder.glob("*.md")) + sorted((folder / "knowledge").glob("*.md"))
            engine = Sentinel(files)
        return engine


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


@app.get("/")
def home():
    return render_template("index.html", max_characters=max_characters)


@app.post("/api/classify")
def classify():
    query, error = read_query()
    if error:
        return error
    return jsonify(classify_text(query))


@app.post("/api/explain")
def explain():
    query, error = read_query()
    if error:
        return error
    return jsonify(explain_text(query))


@app.post("/api/ask")
def ask():
    query, error = read_query(500)
    if error:
        return error
    from sentinel import ollama_ready, role_clearance, answer_model, judge_model
    role = (request.get_json(silent=True) or {}).get("role", "employee")
    if role not in role_clearance:
        return jsonify(error="Unknown role."), 400
    systems = (request.get_json(silent=True) or {}).get("systems") or ["baseline", "neural", "judge"]
    if not isinstance(systems, list) or not set(systems) <= {"baseline", "neural", "judge"}:
        return jsonify(error="Unknown assistant."), 400
    models = ollama_ready()
    if answer_model not in models or ("judge" in systems and judge_model not in models):
        return jsonify(error="The local AI models are not running. Start Ollama (ollama serve) and try again, "
                             "or pick one of the ready-made questions."), 503
    return jsonify(get_engine().ask(query, role, tuple(systems)))


@app.get("/api/suite")
def suite():
    path = data_folder / "suite_results.json"
    if not path.exists():
        return jsonify(error="Run evaluate.py to create the results."), 404
    return app.response_class(path.read_text(), mimetype="application/json")


report_cache = {}


def document_check():
    """Score every sentence of the project's company documents (never used in training)."""
    from sentinel import load_corpus
    chunks = load_corpus()
    results = [classify_text(c["text"]) for c in chunks]
    benign = [r for c, r in zip(chunks, results) if c["truth"] == "benign"]
    attacks = [r for c, r in zip(chunks, results) if c["truth"] != "benign"]
    return {
        "sentences": len(chunks),
        "correct": sum(c["truth"] == r["label"] for c, r in zip(chunks, results)),
        "benign": len(benign),
        "benign_removed": sum(r["action"] == "remove" for r in benign),
        "attacks": len(attacks),
        "attacks_removed": sum(r["action"] == "remove" for r in attacks),
    }


@app.get("/api/model")
def model_report():
    if not report_cache:
        with open(data_folder / "training_history.csv", newline="") as file:
            history = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(file)]
        report_cache.update({
            "architecture": architecture(),
            "test": test_set_report(data_folder / "test.csv"),
            "history": history,
            "training_config": json.loads((data_folder / "training_config.json").read_text()),
            "document_check": document_check(),
        })
    return jsonify(report_cache)


@app.get("/api/industries")
def industries():
    path = data_folder / "industry_results.json"
    if not path.exists():
        return jsonify(error="Run industries.py to create the results."), 404
    return app.response_class(path.read_text(), mimetype="application/json")


@app.get("/api/config")
def config():
    import sentinel
    return jsonify({
        "judge_prompt": sentinel.judge_system,
        "judge_schema": sentinel.judge_schema,
        "role_clearance": sentinel.role_clearance,
        "attack_markers": sentinel.attack_markers,
        "restricted_markers": sentinel.restricted_markers,
        "negation": sentinel.negation.pattern,
    })


@app.get("/api/corpus")
def corpus():
    from sentinel import load_corpus
    return jsonify(load_corpus())


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="The text is too large. Use no more than 10,000 characters."), 413


@app.errorhandler(500)
def server_error(error):
    return jsonify(error="Something went wrong. Please try again."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
