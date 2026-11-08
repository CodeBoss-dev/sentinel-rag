import json
from pathlib import Path

import tiktoken
import torch
import torch.nn as nn


class NeuralNetwork(nn.Module):
    def __init__(self, vocab_size, output_features, hidden_features, max_length, pad_id):
        super().__init__()
        self.pad_id = pad_id
        self.token_embedding = nn.Embedding(vocab_size, hidden_features, padding_idx=pad_id)
        self.position_embedding = nn.Embedding(max_length, hidden_features)
        self.dropout = nn.Dropout(0.3)

        self.layers = nn.ModuleList()
        for _ in range(4):
            layer = nn.TransformerEncoderLayer(
                d_model=hidden_features, nhead=4,
                dim_feedforward=hidden_features * 2,
                dropout=0.3, activation='gelu',
                batch_first=True, norm_first=True,
            )
            self.layers.append(layer)

        self.output_layer = nn.Sequential(
            nn.LayerNorm(hidden_features),
            nn.Dropout(0.3),
            nn.Linear(hidden_features, output_features),
        )

    def forward(self, x):
        padding_mask = x == self.pad_id
        positions = torch.arange(x.shape[1], device=x.device)
        x = self.token_embedding(x) + self.position_embedding(positions)
        x = self.dropout(x)

        for layer in self.layers:
            x = layer(x, src_key_padding_mask=padding_mask)

        return self.output_layer(x[:, 0])


def tokenize_texts(texts, tokenizer, max_length, pad_id):
    sequences = []
    for text in texts:
        ids = [tokenizer.eot_token] + tokenizer.encode_ordinary(text.lower())[:max_length - 1]
        ids = ids + [pad_id] * (max_length - len(ids))
        sequences.append(ids)
    return torch.tensor(sequences, dtype=torch.long).reshape(len(texts), max_length)


def predict(texts, model, settings):
    if not texts:
        return []
    tokenizer = tiktoken.get_encoding(settings['tokenizer_name'])
    x = tokenize_texts(texts, tokenizer, settings['max_length'], settings['pad_id'])
    x = x.to(next(model.parameters()).device)
    model.eval()
    with torch.inference_mode():
        probabilities = torch.softmax(model(x), dim=1).cpu().tolist()

    results = []
    for probs in probabilities:
        label_id = probs.index(max(probs))
        risk_score = 1 - probs[0]
        if not settings['automatic_filtering']:
            action = 'review'
        elif risk_score >= settings['remove_threshold']:
            action = 'remove'
        elif risk_score >= settings['demote_threshold']:
            action = 'demote'
        else:
            action = 'allow'

        results.append({'label': settings['labels'][label_id], 'confidence': probs[label_id],
                        'risk_score': risk_score, 'action': action,
                        'probabilities': dict(zip(settings['labels'], probs))})
    return results


def load_model(folder, device='cpu'):
    folder = Path(folder)
    settings = json.loads((folder / 'model_settings.json').read_text())
    model = NeuralNetwork(
        vocab_size=settings['vocab_size'], output_features=len(settings['labels']),
        hidden_features=settings['hidden_features'], max_length=settings['max_length'],
        pad_id=settings['pad_id'],
    ).to(device)
    weights = torch.load(folder / 'model.pt', map_location=device, weights_only=True)
    model.load_state_dict(weights)
    model.eval()
    return model, settings
