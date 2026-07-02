"""
extract_features.py
Runs filtering + windowing across ALL WESAD subjects, then:
  - extracts statistical/frequency features per window (traditional ML)
  - saves raw normalised sequences per window (for LSTM)
Saves results to data/processed/ so this only needs to run once.
"""

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from scipy.signal import welch
import os

from load_wesad import load_subject
from preprocess import filter_chest_signals, sliding_windows, FS

SUBJECTS = [f"S{i}" for i in [2,3,4,5,6,7,8,9,10,11,13,14,15,16,17]]

OUT_DIR = "data/processed"
os.makedirs(OUT_DIR, exist_ok=True)


def extract_stat_features(signal, prefix):
    feats = {}
    feats[f"{prefix}_mean"] = np.mean(signal)
    feats[f"{prefix}_std"] = np.std(signal)
    feats[f"{prefix}_min"] = np.min(signal)
    feats[f"{prefix}_max"] = np.max(signal)
    feats[f"{prefix}_skew"] = skew(signal)
    feats[f"{prefix}_kurtosis"] = kurtosis(signal)

    zero_crossings = np.sum(np.diff(np.sign(signal)) != 0)
    feats[f"{prefix}_zcr"] = zero_crossings / len(signal)

    freqs, psd = welch(signal, fs=FS, nperseg=min(1024, len(signal)))
    feats[f"{prefix}_peak_freq"] = freqs[np.argmax(psd)]
    feats[f"{prefix}_psd_mean"] = np.mean(psd)

    return feats


def process_all_subjects():
    all_features = []
    all_sequences = []

    for subject in SUBJECTS:
        print(f"Processing {subject}...")
        try:
            d = load_subject(subject)
        except FileNotFoundError:
            print(f"  Skipping {subject} - file not found")
            continue

        filtered = filter_chest_signals(d["chest"])
        windows = sliding_windows(filtered, d["label"])

        for w in windows:
            row = {"subject": subject, "label": w["label"]}
            for ch_name, ch_signal in w["signals"].items():
                row.update(extract_stat_features(ch_signal, ch_name))
            all_features.append(row)

            channels = []
            for ch_name in ["ECG", "EDA", "EMG", "Resp", "Temp"]:
                sig = w["signals"][ch_name]
                sig_norm = (sig - np.mean(sig)) / (np.std(sig) + 1e-8)
                channels.append(sig_norm)
            seq_array = np.stack(channels, axis=-1)
            all_sequences.append({"subject": subject, "label": w["label"], "sequence": seq_array})

        print(f"  {subject}: {len(windows)} windows added")

    feat_df = pd.DataFrame(all_features)
    feat_path = os.path.join(OUT_DIR, "features_traditional.csv")
    feat_df.to_csv(feat_path, index=False)
    print(f"\nSaved traditional features: {feat_path} ({feat_df.shape[0]} rows, {feat_df.shape[1]} columns)")

    seq_path = os.path.join(OUT_DIR, "sequences_lstm.npz")
    np.savez_compressed(
        seq_path,
        sequences=np.array([s["sequence"] for s in all_sequences]),
        labels=np.array([s["label"] for s in all_sequences]),
        subjects=np.array([s["subject"] for s in all_sequences]),
    )
    print(f"Saved LSTM sequences: {seq_path} ({len(all_sequences)} windows)")

    return feat_df


if __name__ == "__main__":
    df = process_all_subjects()
    print("\nClass balance across all subjects:")
    print(df["label"].value_counts())
    print("\nWindows per subject:")
    print(df["subject"].value_counts())