"""The Sentinel-RAG neural guard, re-implemented in NumPy for serverless hosting.

Same weights and the same maths as Project_Frontend/neural_model.py (PyTorch):
token + position embeddings -> 4 pre-norm Transformer encoder layers -> head on the summary token.
"""
import json
import math
import os
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parent.parent
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(root / "tiktoken_cache"))
import tiktoken  # noqa: E402

settings = json.loads((root / "model" / "model_settings.json").read_text())
W = {k: v.astype(np.float64) for k, v in np.load(root / "model" / "weights.npz").items()}
tokenizer = tiktoken.get_encoding(settings["tokenizer_name"])
labels = settings["labels"]
max_length = settings["max_length"]
pad_id = settings["pad_id"]
n_layers = sum(1 for k in W if k.endswith(".self_attn.in_proj_weight"))
d_model = settings["hidden_features"]
n_heads = 4
_erf = np.vectorize(math.erf)


def layer_norm(x, w, b, eps=1e-5):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * w + b


def gelu(x):
    return 0.5 * x * (1.0 + _erf(x / math.sqrt(2.0)))


def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def tokenize(text):
    ids = [tokenizer.eot_token] + tokenizer.encode_ordinary(text.lower())[: max_length - 1]
    return ids + [pad_id] * (max_length - len(ids))


def self_attention(x, p, keep):
    """x: (L, d). Returns output and head-averaged attention weights (L, L)."""
    L = x.shape[0]
    qkv = x @ W[p + "in_proj_weight"].T + W[p + "in_proj_bias"]
    q, k, v = np.split(qkv, 3, axis=-1)
    hd = d_model // n_heads
    q = q.reshape(L, n_heads, hd).transpose(1, 0, 2)
    k = k.reshape(L, n_heads, hd).transpose(1, 0, 2)
    v = v.reshape(L, n_heads, hd).transpose(1, 0, 2)
    scores = q @ k.transpose(0, 2, 1) / math.sqrt(hd)
    scores = np.where(keep[None, None, :], scores, -np.inf)
    attn = softmax(scores, -1)
    out = (attn @ v).transpose(1, 0, 2).reshape(L, d_model)
    out = out @ W[p + "out_proj.weight"].T + W[p + "out_proj.bias"]
    return out, attn.mean(0)


def head(h0):
    z = layer_norm(h0, W["output_layer.0.weight"], W["output_layer.0.bias"])
    return softmax(z @ W["output_layer.2.weight"].T + W["output_layer.2.bias"])


def forward(ids, trace=False):
    ids = np.array(ids)
    keep = ids != pad_id
    h = W["token_embedding.weight"][ids] + W["position_embedding.weight"][: len(ids)]
    embedding_strength = np.linalg.norm(h, axis=-1)
    layers = []
    for i in range(n_layers):
        p = f"layers.{i}."
        a, weights = self_attention(layer_norm(h, W[p + "norm1.weight"], W[p + "norm1.bias"]), p + "self_attn.", keep)
        h = h + a
        f = layer_norm(h, W[p + "norm2.weight"], W[p + "norm2.bias"])
        f = gelu(f @ W[p + "linear1.weight"].T + W[p + "linear1.bias"]) @ W[p + "linear2.weight"].T + W[p + "linear2.bias"]
        h = h + f
        if trace:
            layers.append({"weights": weights[0], "probabilities": head(h[0])})
    return head(h[0]), embedding_strength, layers


def decide(probs):
    label_id = int(np.argmax(probs))
    risk = float(1 - probs[0])
    if not settings["automatic_filtering"]:
        action = "review"
    elif risk >= settings["remove_threshold"]:
        action = "remove"
    elif risk >= settings["demote_threshold"]:
        action = "demote"
    else:
        action = "allow"
    return {"label": labels[label_id], "confidence": float(probs[label_id]), "risk_score": risk, "action": action,
            "probabilities": dict(zip(labels, map(float, probs)))}


def classify_text(query):
    probs, _, _ = forward(tokenize(query))
    result = decide(probs)
    token_count = len(tokenizer.encode_ordinary(query.lower()))
    result["token_count"] = token_count
    result["tokens_used"] = min(token_count, max_length - 1)
    result["truncated"] = token_count > max_length - 1
    return result


def explain_text(query):
    result = classify_text(query)
    ids = tokenize(query)
    length = sum(1 for i in ids if i != pad_id)
    _, strength, layers = forward(ids, trace=True)
    result["tokens"] = [tokenizer.decode([i]) for i in ids[1:length]]
    result["embedding_strength"] = strength[1:length].tolist()
    result["layers"] = [{"attention": l["weights"][1:length].tolist(),
                         "probabilities": dict(zip(labels, map(float, l["probabilities"])))} for l in layers]
    return result
