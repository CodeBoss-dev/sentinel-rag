Extract the ZIP into one folder. Install requirements.txt if needed.

from neural_model import load_model, predict
model, settings = load_model('path/to/extracted_folder')
results = predict(['Your text here'], model, settings)
print(results)

model.pt contains learned weights; model_settings.json contains their settings.
The tokenizer is predefined. All neural weights were trained from scratch.
Metrics describe a synthetic benchmark. Actual source permissions must be
checked separately. If automatic_filtering is false, actions are review.
