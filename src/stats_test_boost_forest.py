"""
stats_test_boost_forest.py

Paired subject-level statistical comparison of Boost Forest v2 against
XGBoost and Random Forest using the same LOSO subjects.

Outputs:
- models/boost_forest_v2_wilcoxon_results.csv

For each metric:
- mean score for each model
- mean paired difference
- wins / losses / ties for Boost Forest v2
- two-sided Wilcoxon signed-rank p-value
- rank-biserial effect size
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon, rankdata

BOOST_PATH = "models/boost_forest_v2_loso_results.csv"
XGB_PATH = "models/xgb_loso_results.csv"
RF_PATH = "models/rf_loso_results.csv"
OUT_PATH = "models/boost_forest_v2_wilcoxon_results.csv"

METRICS = ["accuracy", "precision", "recall", "f1_macro", "roc_auc"]


def load_results(path, suffix):
    df = pd.read_csv(path)
    needed = ["subject"] + METRICS
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    return df[needed].rename(
        columns={m: f"{m}_{suffix}" for m in METRICS}
    )


def rank_biserial_from_differences(diffs):
    diffs = np.asarray(diffs, dtype=float)
    diffs = diffs[np.isfinite(diffs)]
    diffs = diffs[diffs != 0]

    if len(diffs) == 0:
        return 0.0

    ranks = rankdata(np.abs(diffs), method="average")
    w_pos = ranks[diffs > 0].sum()
    w_neg = ranks[diffs < 0].sum()

    denom = w_pos + w_neg
    if denom == 0:
        return 0.0

    return float((w_pos - w_neg) / denom)


def compare_pair(boost, other, other_name, other_suffix):
    merged = boost.merge(other, on="subject", how="inner", validate="one_to_one")

    rows = []

    for metric in METRICS:
        a = merged[f"{metric}_boost"].astype(float)
        b = merged[f"{metric}_{other_suffix}"].astype(float)

        valid = a.notna() & b.notna()
        a = a[valid].to_numpy()
        b = b[valid].to_numpy()

        diffs = a - b

        wins = int(np.sum(diffs > 1e-12))
        losses = int(np.sum(diffs < -1e-12))
        ties = int(len(diffs) - wins - losses)

        nonzero = diffs[np.abs(diffs) > 1e-12]

        if len(nonzero) == 0:
            statistic = 0.0
            p_value = 1.0
        else:
            test = wilcoxon(
                a,
                b,
                zero_method="wilcox",
                alternative="two-sided",
                method="auto",
            )
            statistic = float(test.statistic)
            p_value = float(test.pvalue)

        rows.append({
            "metric": metric,
            "comparison": f"boost_forest_v2_vs_{other_name}",
            "n_subjects": int(len(diffs)),
            "boost_forest_v2_mean": float(np.mean(a)),
            f"{other_name}_mean": float(np.mean(b)),
            "mean_difference_boost_minus_other": float(np.mean(diffs)),
            "boost_wins": wins,
            "boost_losses": losses,
            "ties": ties,
            "wilcoxon_statistic": statistic,
            "p_value": p_value,
            "significant_0.05": bool(p_value < 0.05),
            "rank_biserial_effect_size": rank_biserial_from_differences(diffs),
        })

    return rows


def main():
    if not os.path.exists(BOOST_PATH):
        raise FileNotFoundError(BOOST_PATH)
    if not os.path.exists(XGB_PATH):
        raise FileNotFoundError(XGB_PATH)
    if not os.path.exists(RF_PATH):
        raise FileNotFoundError(RF_PATH)

    boost = load_results(BOOST_PATH, "boost")
    xgb = load_results(XGB_PATH, "xgb")
    rf = load_results(RF_PATH, "rf")

    rows = []
    rows.extend(compare_pair(boost, xgb, "xgboost", "xgb"))
    rows.extend(compare_pair(boost, rf, "random_forest", "rf"))

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 180)

    print("\n" + "=" * 90)
    print("BOOST FOREST v2 — PAIRED LOSO STATISTICAL COMPARISON")
    print("=" * 90)

    display_cols = [
        "metric",
        "comparison",
        "boost_forest_v2_mean",
        "mean_difference_boost_minus_other",
        "boost_wins",
        "boost_losses",
        "ties",
        "p_value",
        "significant_0.05",
        "rank_biserial_effect_size",
    ]

    print(out[display_cols].round(6).to_string(index=False))
    print(f"\nSaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
