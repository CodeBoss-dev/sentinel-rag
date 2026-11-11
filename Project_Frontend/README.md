# Sentinel-RAG dashboard

One web app that shows the whole project: three RAG assistants (no guard,
neural guard, LLM judge) answering the same questions from the same company
files, plus a visual look inside the scratch-trained neural classifier.

## Run

```bash
ollama serve                       # in its own terminal (needed only for live questions)
cd Project_Frontend
../Project_Code/.venv/bin/python app.py
```

Open http://127.0.0.1:5001. Models needed for live questions: `llama3.2:3b`
(answer writer) and `gemma2:2b` (judge). Without Ollama, the suggested questions
on the Assistant tab replay their saved answers instantly.

## The five tabs

| Tab | For | Shows |
|---|---|---|
| Overview | Anyone | Animated "idea in one picture", headline numbers, six comparison charts and a ✓/✕ grid of every test question. |
| Assistant | Anyone who wants to try the product | A chat window like the one an employee would use: pick who is signed in and which protection is on, ask a question, and switch protection off to see the difference. Runs live when Ollama is on; otherwise the suggested questions replay their saved answers. A second view compares all three assistants side by side. |
| Who it's for | Business audiences | Pick a bank, hospital, law firm or online store: a four-panel story of a real test run on that organisation's files (question → planted fake order → fooled vs. protected answer), plain-language benefits, India breach-cost chart (IBM 2026), how the guard fits in, and a ✓/✕ grid across all 8 industry tests. |
| The Brain | Anyone | Animated diagram of the neural network running on any message you type, the words it focused on, how its decision builds layer by layer, a report card and the learning curve. |
| Technical | Examiners who want depth | Setup, full metric tables per scenario, every saved answer, confusion matrix, precision/recall/F1, risk-score histogram with thresholds, training curves, judge prompt/schema and agreement rates, scoring method, limitations, and the whole knowledge base. |

## Files

```text
app.py          Flask routes (page + JSON API)
sentinel.py     Shared RAG core and the three security variants
evaluate.py     Runs the 25-question suite in two scenarios → data/suite_results.json
industries.py   Runs 8 industry questions on industries/*/ → data/industry_results.json
knowledge/      Extended company files (HR, IT, travel, security, office) searched only by live questions;
                the saved test suite and all reported numbers use Project_Code/documents/ alone
industries/     Synthetic files for a bank, hospital, law firm and online store
inference.py    Neural classifier: classify, explain (attention + per-layer readout), test report
neural_model.py Exported PyTorch architecture
model/          Trained weights and settings
data/           Saved suite results, training history/config, held-out test set
templates/      index.html
static/         style.css, charts.js (dependency-free SVG charts), app.js
```

## Re-running the evaluation

```bash
../Project_Code/.venv/bin/python evaluate.py            # ~15 min, needs Ollama
../Project_Code/.venv/bin/python evaluate.py --rescore  # re-score saved answers only
```

Scenarios: **Everyday company** (all documents) and **Under heavy attack**
(official policy file removed, so attacker messages dominate retrieval).
Hand-review corrections to the automatic "tricked?" check go in
`data/review_overrides.json` as `{"scenario/question_id/system": {"tricked": false}}`.

## Notes

- The neural guard and judge both apply role-based access control first;
  the baseline deliberately has no checks (control group).
- Every test-set number is recomputed live from the deployed weights.
  The training curve comes from the exported v2 training run; the deployed
  weights are a later retrain whose per-epoch history was not exported.
- All data is synthetic. The server listens only on this computer.
