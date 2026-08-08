"""
create_final_model_comparison.py

Creates a dissertation-ready four-model comparison table and figure
from the existing LOSO result files.

Outputs:
- models/final_model_comparison_4models.csv
- notebooks/final_model_comparison_4models.png
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

FILES = {
    "Random Forest": Path("models/rf_loso_results.csv"),
    "XGBoost": Path("models/xgb_loso_results.csv"),
    "Tuned LSTM": Path("models/lstm_loso_results_tuned.csv"),
    "Boost Forest": Path("models/boost_forest_v2_loso_results.csv"),
}

METRICS = ["accuracy", "precision", "recall", "f1_macro", "roc_auc"]

rows = []
for model_name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    missing = [m for m in METRICS if m not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing metrics: {missing}")

    row = {"model": model_name, "n_subjects": len(df)}
    for metric in METRICS:
        row[f"{metric}_mean"] = df[metric].mean()
        row[f"{metric}_sd"] = df[metric].std()
    rows.append(row)

summary = pd.DataFrame(rows)

out_csv = Path("models/final_model_comparison_4models.csv")
summary.to_csv(out_csv, index=False)

print("\nFOUR-MODEL LOSO COMPARISON")
print("=" * 88)
display_cols = [
    "model",
    "accuracy_mean",
    "precision_mean",
    "recall_mean",
    "f1_macro_mean",
    "roc_auc_mean",
]
print(summary[display_cols].round(4).to_string(index=False))

# Plot mean LOSO scores for the five main metrics.
plot_df = summary.set_index("model")[
    [
        "accuracy_mean",
        "precision_mean",
        "recall_mean",
        "f1_macro_mean",
        "roc_auc_mean",
    ]
].copy()

plot_df.columns = ["Accuracy", "Precision", "Recall", "F1-macro", "ROC-AUC"]

fig, ax = plt.subplots(figsize=(10, 6))
plot_df.plot(kind="bar", ax=ax)
ax.set_ylim(0, 1)
ax.set_ylabel("Mean LOSO score")
ax.set_xlabel("")
ax.set_title("Four-Model Performance Comparison Across 15 LOSO Folds")
ax.legend(title="Metric", ncol=3)
ax.grid(axis="y", alpha=0.25)
plt.xticks(rotation=0)
plt.tight_layout()

out_png = Path("notebooks/final_model_comparison_4models.png")
out_png.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out_png, dpi=220)
plt.close(fig)

print(f"\nSaved table:  {out_csv}")
print(f"Saved figure: {out_png}")
print(
    "\nInterpretation note: Boost Forest has the highest mean Accuracy, "
    "Precision, F1-macro and ROC-AUC, but the Wilcoxon tests show that "
    "its improvements over XGBoost are not statistically significant."
)
