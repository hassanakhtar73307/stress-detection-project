"""
tune_lstm.py
Runs a small Keras Tuner random search for the LSTM architecture,
on a held-out subject-grouped validation split (consistent with the
RF/XGBoost tuning approach in tune_hyperparameters.py). Kept small
(few trials, few epochs) to be time-tractable.
"""
import numpy as np
import pandas as pd
import keras_tuner as kt
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import GroupShuffleSplit
from sklearn.utils.class_weight import compute_class_weight
import json

DOWNSAMPLE_FACTOR = 100

data = np.load("data/processed/sequences_lstm.npz", allow_pickle=True)
sequences = data["sequences"][:, ::DOWNSAMPLE_FACTOR, :]
labels = data["labels"]
subjects = data["subjects"]

y = labels - 1  # 0-indexed

splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
train_idx, val_idx = next(splitter.split(sequences, y, subjects))
X_train, X_val = sequences[train_idx], sequences[val_idx]
y_train, y_val = y[train_idx], y[val_idx]
print(f"Train: {len(X_train)} windows, Val: {len(X_val)} windows")

classes = np.unique(y_train)
weights = compute_class_weight("balanced", classes=classes, y=y_train)
class_weight = {c: w for c, w in zip(classes, weights)}

def build_model(hp):
    n_layers = hp.Int("n_layers", 1, 2)
    units = hp.Choice("units", [32, 64, 128])
    dropout = hp.Float("dropout", 0.2, 0.5, step=0.1)

    model = keras.Sequential()
    model.add(layers.Input(shape=X_train.shape[1:]))
    for i in range(n_layers):
        return_seq = i < n_layers - 1
        model.add(layers.LSTM(units, return_sequences=return_seq))
        model.add(layers.Dropout(dropout))
    model.add(layers.Dense(3, activation="softmax"))
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model

tuner = kt.RandomSearch(
    build_model,
    objective="val_accuracy",
    max_trials=5,
    executions_per_trial=1,
    directory="models/keras_tuner",
    project_name="lstm_search",
    overwrite=True,
)

early_stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)

tuner.search(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=10,
    batch_size=32,
    class_weight=class_weight,
    callbacks=[early_stop],
    verbose=1,
)

best_hp = tuner.get_best_hyperparameters(1)[0]
best_model = tuner.get_best_models(1)[0]
val_loss, val_acc = best_model.evaluate(X_val, y_val, verbose=0)

print("\n" + "=" * 50)
print("BEST HYPERPARAMETERS FOUND")
print("=" * 50)
print(f"n_layers: {best_hp.get('n_layers')}")
print(f"units: {best_hp.get('units')}")
print(f"dropout: {best_hp.get('dropout')}")
print(f"Validation accuracy: {val_acc:.3f}")

results = {
    "n_layers": best_hp.get("n_layers"),
    "units": best_hp.get("units"),
    "dropout": best_hp.get("dropout"),
    "val_accuracy": float(val_acc),
    "val_loss": float(val_loss),
}
with open("models/lstm_tuning_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved models/lstm_tuning_results.json")