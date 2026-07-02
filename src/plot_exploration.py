"""
plot_exploration.py
Plots a few minutes of chest ECG, EDA, and Respiration for one WESAD subject,
colour-coded by label (baseline / stress / amusement), as a first EDA deliverable.
"""

import matplotlib.pyplot as plt
import numpy as np
from load_wesad import load_subject

def plot_subject_overview(subject_id="S2", data_dir="data/WESAD", fs=700):
    d = load_subject(subject_id, data_dir)
    label = d["label"]
    ecg = d["chest"]["ECG"].flatten()
    eda = d["chest"]["EDA"].flatten()
    resp = d["chest"]["Resp"].flatten()

    t = np.arange(len(label)) / fs / 60

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

    label_colors = {1: "#a8d5a2", 2: "#f4a3a3", 3: "#a3c9f4"}

    for ax, signal, name in zip(axes, [ecg, eda, resp], ["ECG", "EDA", "Respiration"]):
        ax.plot(t, signal, linewidth=0.5, color="black")
        ax.set_ylabel(name)

        prev_label = label[0]
        start_idx = 0
        for i in range(1, len(label)):
            if label[i] != prev_label:
                if prev_label in label_colors:
                    ax.axvspan(t[start_idx], t[i], color=label_colors[prev_label], alpha=0.3)
                start_idx = i
                prev_label = label[i]

    axes[-1].set_xlabel("Time (minutes)")
    axes[0].set_title(f"Subject {subject_id} — Chest Signals (green=baseline, red=stress, blue=amusement)")

    plt.tight_layout()
    out_path = f"notebooks/{subject_id}_signal_overview.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")
    plt.show()


if __name__ == "__main__":
    plot_subject_overview("S2")