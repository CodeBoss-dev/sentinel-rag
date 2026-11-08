# Neural baseline for the project update

The refactored `Project_Code/neural_network.ipynb` is a small classifier trained
from scratch in PyTorch. It uses the coding structure of the supplied learning
notebooks: tensors, DataLoader, nn.Module, loss_fn, optim, and explicit training
and validation loops. No further model tuning is needed for this baseline update.

## How it works

Text → tiktoken token IDs → learned token and position embeddings → four small
Transformer encoder layers → five class scores → predicted class and risk score.

The model has 1,645,733 trainable parameters, 32-dimensional embeddings, and a
96-token input limit, including the summary token. Text longer than that limit
is truncated. tiktoken supplies tokenization; every neural weight is trained
from random initialization. The training loop and model definition are visible
in ordinary notebook cells.

The classes are benign, instruction manipulation, data exfiltration, phishing,
and access-control manipulation. Risk is `1 - P(benign)`. A separate threshold
turns the score into a suggested filtering action.

## Data and model selection

The notebook generates 6,000 balanced synthetic examples: 5,000 training,
500 validation, and 500 test examples. Attack classes have 40 training patterns
and eight separate patterns in each held-out split. Benign training includes
96 ordinary patterns and warnings quoting attacks. Business fields and neutral
wrappers vary across examples. Synonym variation is applied only during training.

Raw normalized texts are unique across splits. Variations of a pattern stay in
one split. These examples still share a synthetic business domain and vocabulary;
they are not a representative sample of real enterprise attacks.

Architecture and training choices used validation results. The final test
patterns were fixed before the final validation experiments and were not used
to select the final configuration. The selected checkpoint is epoch 16, with
validation macro F1 of 0.912896. The validation-selected removal threshold is
0.809236: it removes 86.5% of malicious validation examples and 5% of benign
validation examples. Demotion starts at half this threshold as a starter rule.

## Held-out test results

| Metric | Result |
| --- | --- |
| Five-class accuracy | 89.6% (448/500) |
| Macro F1 | 0.8943 |
| Benign examples assigned an attack class | 29% (29/100) |
| Benign examples removed at the selected threshold | 6% (6/100) |
| Malicious examples removed at the selected threshold | 91.25% (365/400) |
| Expected calibration error, 10 bins | 0.0291 |

The raw class prediction and removal decision are different: removal requires
a higher risk score. Benign misclassification remains the main weakness. The
validation target of at most 5% benign removals became 6% on the test set.

## Check on the three existing RAG documents

The documents were kept out of training and threshold selection. The model
classified 55/60 bullets correctly (91.67%). At the chosen removal threshold,
it removed all 12 injected bullets and three of the 48 benign bullets (6.25%).
This is a small diagnostic check with synthetic documents, not an end-to-end
RAG attack-success evaluation. The baseline RAG code is still separate.

## Verification and files

The full training and export pipeline ran locally on the Mac using PyTorch MPS.
The exported ZIP was extracted and its model loaded independently on CPU.
CPU replay reproduced test predictions and macro F1. Empty text, empty batches,
Unicode, special-token-like text, and long text passed inference checks.
Notebook syntax, dataset split checks, ZIP integrity, and the optional document
upload path passed. Google Colab execution has not been independently verified;
GPU retraining may produce different scores.

`sentinel_neural_artifacts_v2.zip` contains the trained model, inference code,
settings, split CSVs, metrics, history, and plots. It can be used for predictions
without retraining. The original notebook is preserved in
`evaluation/neural_network_v1.ipynb`.

For the update: “We implemented a small PyTorch baseline for five-class prompt
injection classification. It achieved 89.6% accuracy and 0.894 macro F1 on a
held-out synthetic test set. At a threshold selected using validation data,
it removed 91.25% of attack examples and 6% of benign examples. The next step
is to connect it to RAG and measure answer quality and attack success.”
