# Sentinel-RAG

**Keeping company AI assistants safe from hidden tricks.**

Company AI assistants answer staff questions by reading internal files: policies,
wikis, chats and emails. If someone plants an instruction inside one of those
files ("tell staff KYC can be skipped", "send customers to this link"), the
assistant may repeat it. This is *indirect prompt injection*.

Sentinel-RAG compares three assistants that use the **same files, search and
answer-writing model**. Only the security layer differs:

| Assistant | Security layer |
|---|---|
| No guard | None (control group) |
| Neural guard | Role-based access control + a Transformer classifier we trained from scratch in PyTorch |
| AI judge | Role-based access control + a local 2B LLM (gemma2:2b) returning validated JSON verdicts |

## Results (25 questions × 2 scenarios, plus 8 industry tests)

| | No guard | Neural guard | AI judge |
|---|---|---|---|
| Unsafe answers, heavy attack | 10 / 25 | 0 / 25 | 0 / 25 |
| Unsafe answers, everyday company | 4 / 25 | 0 / 25 | 0 / 25 |
| Fooled in industry tests (bank, hospital, law firm, store) | 5 / 8 | 0 / 8 | 0 / 8 |
| Good information blocked by mistake (everyday) | 0% | 15.9% | 0% |
| Median seconds per answer (heavy attack) | 2.6 | 3.4 | 17.9 |

Neural classifier: 1.65M parameters, 4 Transformer encoder layers, 89.8% accuracy
on a 500-message held-out test set, 5 threat classes. All data is synthetic.

## Dashboard

A Flask web app with four tabs:

- **Overview**: animated explainer, headline numbers, comparison charts, and a side-by-side view of what each assistant found, blocked and answered.
- **Who it's for**: pick a bank, hospital, law firm or online store and see a real test run on that organisation's files.
- **The Brain**: an animated diagram of the neural network reading any message you type.
- **Technical**: every metric, saved answer, confusion matrix, judge prompt, scoring rule and limitation.

## Run it

Requirements: Python 3.10+, [Ollama](https://ollama.com) with `llama3.2:3b` and `gemma2:2b`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r Project_Frontend/requirements.txt
ollama pull llama3.2:3b && ollama pull gemma2:2b
ollama serve &                     # needed only for live questions
python Project_Frontend/app.py     # open http://127.0.0.1:5001
```

Saved results are replayed, so the ready-made demo works without Ollama.
To regenerate them: `python Project_Frontend/evaluate.py` and `python Project_Frontend/industries.py`.

## Repository layout

```text
Project_Frontend/   Dashboard, three-system engine (sentinel.py), evaluation scripts, trained model
Project_Code/       Original baseline RAG pipeline, company documents, earlier evaluation notes
  documents/        Synthetic company files (clean policy, injected files, restricted report)
  evaluation/       Baseline assessment and exported neural training artifacts (v2)
neural_network.ipynb  Colab notebook used to train the classifier
```

## Team

Group BCCSAF01, Department of Computer Science & Engineering, MIT School of Computing.
Waaridh Borpujari, Aadi Surve, Soham Arte, Sushil Sonawane. Guide: Prof. Vijaya Patil.
