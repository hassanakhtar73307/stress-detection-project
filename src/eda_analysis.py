"""
eda_analysis.py
Generates the exploratory data analysis plots for the Weeks 3-4 deliverable:
  1. Class balance bar chart
  2. Correlation heatmap of features
  3. Boxplots of key features by class (baseline/stress/amusement)
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

DATA_PATH = "data/processed/features_traditional.csv"
OUT_DIR = "notebooks"
os.makedirs(OUT_DIR, exist_ok=True)

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}


def load_data():
    df = pd.read_csv(DATA_PATH)
    df["label_name"] = df["label"].map(LABEL_NAMES)
    return df


def plot_class_balance(df):
    plt.figure(figsize=(6, 4))
    order = ["Baseline", "Stress", "Amusement"]
    palette = {"Baseline": "#a8d5a2", "Stress": "#f4a3a3", "Amusement": "#a3c9f4"}
    sns.countplot(data=df, x="label_name", order=order, hue="label_name", palette=palette, legend=False)
    plt.title("Class Balance Across All Subjects (1105 windows)")
    plt.xlabel("Class")
    plt.ylabel("Number of windows")
    plt.tight_layout()
    path = os.path.join(OUT_DIR, "class_balance.png")
    plt.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close()


def plot_correlation_heatmap(df):
    feature_cols = [c for c in df.columns if c not in ("subject", "label", "label_name")]
    corr = df[feature_cols].corr()

    plt.figure(figsize=(16, 14))
    sns.heatmap(corr, cmap="coolwarm", center=0, square=True, cbar_kws={"shrink": 0.6})
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    path = os.path.join(OUT_DIR, "correlation_heatmap.png")
    plt.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close()


def plot_key_boxplots(df):
    key_features = ["EDA_mean", "ECG_std", "Resp_std", "EMG_mean"]
    key_features = [f for f in key_features if f in df.columns]

    order = ["Baseline", "Stress", "Amusement"]
    colors = ["#a8d5a2", "#f4a3a3", "#a3c9f4"]

    fig, axes = plt.subplots(1, len(key_features), figsize=(4 * len(key_features), 5))
    if len(key_features) == 1:
        axes = [axes]

    for ax, feat in zip(axes, key_features):
        data_by_class = [df[df["label_name"] == cls][feat].values for cls in order]
        bp = ax.boxplot(data_by_class, tick_labels=order, patch_artist=True)
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
        ax.set_title(feat)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "key_feature_boxplots.png")
    plt.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.close()


if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns")

    plot_class_balance(df)
    plot_correlation_heatmap(df)
    plot_key_boxplots(df)

    print("\nAll EDA plots saved to notebooks/")