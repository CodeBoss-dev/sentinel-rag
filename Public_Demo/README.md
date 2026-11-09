# Sentinel-RAG public demo

Live: https://sentinel-rag-two.vercel.app

Serverless copy of the Sentinel-RAG dashboard for Vercel. It replays the saved test runs and runs the
scratch-trained classifier live in NumPy (same weights as the PyTorch model, outputs match to 1e-6).
Asking new questions to all three assistants needs the local Ollama models, so it is disabled here.

Local test:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python api/index.py
Deploy:      npx vercel --prod
