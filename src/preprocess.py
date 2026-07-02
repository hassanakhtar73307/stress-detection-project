"""
preprocess.py
Filters chest signals and segments them into sliding windows with labels.
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt
from load_wesad import load_subject

FS = 700  # chest sampling rate in Hz

def bandpass_filter(signal, lowcut, highcut, fs=FS, order=3):
    """Apply a Butterworth bandpass filter to a 1D signal using SOS form
    for numerical stability (narrow-band filters, e.g. Resp 0.1-0.35Hz,
    are unstable in transfer-function 'ba' form and silently produce NaN)."""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    sos = butter(order, [low, high], btype="band", output="sos")
    return sosfiltfilt(sos, signal)


def filter_chest_signals(chest):
    filtered = {}
    filtered["ECG"] = bandpass_filter(chest["ECG"].flatten(), 0.5, 40)
    filtered["EDA"] = chest["EDA"].flatten()
    filtered["EMG"] = bandpass_filter(chest["EMG"].flatten(), 20, 250)
    filtered["Resp"] = bandpass_filter(chest["Resp"].flatten(), 0.1, 0.35)
    filtered["Temp"] = chest["Temp"].flatten()
    return filtered


def sliding_windows(signal_dict, label, window_sec=60, overlap=0.5, fs=FS):
    window_size = int(window_sec * fs)
    step_size = int(window_size * (1 - overlap))
    n_samples = len(label)

    windows = []
    for start in range(0, n_samples - window_size, step_size):
        end = start + window_size
        window_label_slice = label[start:end]

        values, counts = np.unique(window_label_slice, return_counts=True)
        majority_label = values[np.argmax(counts)]

        if majority_label not in (1, 2, 3):
            continue

        window_signals = {k: v[start:end] for k, v in signal_dict.items()}
        windows.append({"signals": window_signals, "label": int(majority_label)})

    return windows


if __name__ == "__main__":
    subject = "S2"
    d = load_subject(subject)
    filtered = filter_chest_signals(d["chest"])
    windows = sliding_windows(filtered, d["label"])

    print(f"Subject {subject}: created {len(windows)} windows")
    labels = [w["label"] for w in windows]
    values, counts = np.unique(labels, return_counts=True)
    for v, c in zip(values, counts):
        name = {1: "baseline", 2: "stress", 3: "amusement"}[v]
        print(f"  Label {v} ({name}): {c} windows")