"""
load_wesad.py
Loads a single WESAD subject's pickled data and provides basic access
to chest and wrist signals plus labels.
"""

import pickle
import numpy as np
import os

def load_subject(subject_id, data_dir="data/WESAD"):
    pkl_path = os.path.join(data_dir, subject_id, f"{subject_id}.pkl")
    if not os.path.exists(pkl_path):
        raise FileNotFoundError(f"Could not find {pkl_path}")

    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")

    chest = data["signal"]["chest"]
    wrist = data["signal"]["wrist"]
    label = np.array(data["label"])

    return {"chest": chest, "wrist": wrist, "label": label}


if __name__ == "__main__":
    subject = "S2"
    d = load_subject(subject)

    print(f"Loaded subject {subject}")
    print("Chest signal keys:", list(d["chest"].keys()))
    print("Wrist signal keys:", list(d["wrist"].keys()))
    print("Chest ECG shape:", d["chest"]["ECG"].shape)
    print("Label array shape:", d["label"].shape)
    print("Unique labels present:", np.unique(d["label"]))