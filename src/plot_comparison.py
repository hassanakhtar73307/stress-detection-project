import pandas as pd
import matplotlib.pyplot as plt

rf = pd.read_csv("models/rf_loso_results.csv")
xgb = pd.read_csv("models/xgb_loso_results.csv")
lstm = pd.read_csv("models/lstm_loso_results.csv")

models = ["Random Forest", "XGBoost", "LSTM"]
means = [rf["f1_macro"].mean(), xgb["f1_macro"].mean(), lstm["f1_macro"].mean()]
stds = [rf["f1_macro"].std(), xgb["f1_macro"].std(), lstm["f1_macro"].std()]

fig, ax = plt.subplots(figsize=(6, 5))
bars = ax.bar(models, means, yerr=stds, capsize=8, color=["#4C72B0", "#55A868", "#C44E52"])
ax.set_ylabel("F1-macro (mean ± SD across 15 LOSO folds)")
ax.set_title("Model Comparison: LOSO F1-macro with Per-Subject Variance")
ax.set_ylim(0, 1)
for bar, m in zip(bars, means):
    ax.text(bar.get_x() + bar.get_width()/2, m + 0.02, f"{m:.3f}", ha="center", fontweight="bold")

plt.tight_layout()
plt.savefig("notebooks/model_comparison_barchart.png", dpi=150)
print("Saved notebooks/model_comparison_barchart.png")