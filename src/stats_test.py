import pandas as pd
import numpy as np

def rank_biserial(a, b):
    diffs = np.array(a) - np.array(b)
    diffs = diffs[diffs != 0]
    n = len(diffs)
    pos = np.sum(diffs > 0)
    neg = np.sum(diffs < 0)
    return (pos - neg) / n
from scipy.stats import wilcoxon

# Load per-subject LOSO results
rf = pd.read_csv("models/rf_loso_results.csv")
xgb = pd.read_csv("models/xgb_loso_results.csv")
lstm = pd.read_csv("models/lstm_loso_results_tuned.csv")

# Merge on subject so rows line up correctly (Wilcoxon needs matched pairs)
merged = rf[["subject", "accuracy", "f1_macro"]].merge(
    xgb[["subject", "accuracy", "f1_macro"]], on="subject", suffixes=("_rf", "_xgb")
).merge(
    lstm[["subject", "accuracy", "f1_macro"]].rename(
        columns={"accuracy": "accuracy_lstm", "f1_macro": "f1_macro_lstm"}
    ),
    on="subject"
)

print("Merged per-subject results:")
print(merged)
print()

pairs = [
    ("rf", "xgb"),
    ("xgb", "lstm"),
    ("rf", "lstm"),
]

results = []

for metric in ["accuracy", "f1_macro"]:
    print(f"=== Wilcoxon signed-rank test: {metric} ===")
    for a, b in pairs:
        col_a = f"{metric}_{a}"
        col_b = f"{metric}_{b}"
        stat, p = wilcoxon(merged[col_a], merged[col_b])
        effect = rank_biserial(merged[col_a], merged[col_b])
        sig = "significant (p<0.05)" if p < 0.05 else "not significant"
        print(f"  {a.upper()} vs {b.upper()}: statistic={stat:.3f}, p={p:.4f} -> {sig}")
        print(f"    effect size (rank-biserial r) = {effect:.3f}")
        results.append({
            "metric": metric,
            "comparison": f"{a}_vs_{b}",
            "statistic": stat,
            "p_value": p,
            "significant_0.05": p < 0.05,
            "effect_size_r": effect
        })
    print()

results_df = pd.DataFrame(results)
results_df.to_csv("models/wilcoxon_results.csv", index=False)
print("Saved results to models/wilcoxon_results.csv")