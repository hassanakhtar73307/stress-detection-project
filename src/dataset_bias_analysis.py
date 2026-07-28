"""
dataset_bias_analysis.py
Analyses the WESAD dataset's subject composition and class balance to
provide concrete numbers for the dissertation's Limitations section
(dataset bias, generalisability, deployment constraints), rather than a
vague, uncited claim about possible bias.

Uses the subject metadata that ships with WESAD's readme_S*.txt files if
available; falls back to reporting class/subject distribution from the
already-extracted feature data if the raw WESAD folder is no longer present
(as is the case after feature extraction has already been run once).

Run from the project root:
    python src\\dataset_bias_analysis.py
"""
import os
import re
import pandas as pd

WESAD_DIR = "data/WESAD"
FEATURES_PATH = "data/processed/features_traditional.csv"
OUT_DIR = "models"

LABEL_NAMES = {1: "Baseline", 2: "Stress", 3: "Amusement"}


def parse_readme_metadata():
    """Parses age/gender from WESAD's per-subject readme files, if present."""
    records = []
    if not os.path.isdir(WESAD_DIR):
        return None

    for subj_dir in sorted(os.listdir(WESAD_DIR)):
        readme_path = os.path.join(WESAD_DIR, subj_dir, f"{subj_dir}_readme.txt")
        if not os.path.exists(readme_path):
            continue
        with open(readme_path, "r", errors="ignore") as f:
            text = f.read()

        age_match = re.search(r"Age:\s*(\d+)", text)
        gender_match = re.search(r"Gender:\s*(\w+)", text)
        records.append({
            "subject": subj_dir,
            "age": int(age_match.group(1)) if age_match else None,
            "gender": gender_match.group(1) if gender_match else None,
        })
    return pd.DataFrame(records) if records else None


def class_distribution_from_features():
    """Falls back to reporting class balance from the extracted feature CSV,
    which is always available once the pipeline has run once, even if the
    raw WESAD folder has since been deleted to save disk space."""
    df = pd.read_csv(FEATURES_PATH)
    per_subject = df.groupby(["subject", "label"]).size().unstack(fill_value=0)
    per_subject.columns = [LABEL_NAMES.get(c, c) for c in per_subject.columns]
    overall = df["label"].value_counts().rename(index=LABEL_NAMES)
    return per_subject, overall


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 55)
    print("WESAD DATASET BIAS / GENERALISABILITY ANALYSIS")
    print("=" * 55)

    demo_df = parse_readme_metadata()
    if demo_df is not None and demo_df["age"].notna().any():
        print(f"\nSubject demographics (n={len(demo_df)}):")
        print(f"  Age: mean={demo_df['age'].mean():.1f}, "
              f"min={demo_df['age'].min()}, max={demo_df['age'].max()}")
        if demo_df["gender"].notna().any():
            print("  Gender distribution:")
            print(demo_df["gender"].value_counts().to_string())
        demo_df.to_csv(os.path.join(OUT_DIR, "wesad_subject_demographics.csv"), index=False)
        print(f"\nSaved to {OUT_DIR}/wesad_subject_demographics.csv")
    else:
        print("\nRaw WESAD readme files not found (likely deleted after feature "
              "extraction to save disk space). Demographic breakdown by age/gender "
              "is not available from this machine's current state.")
        print("NOTE for dissertation: WESAD's published documentation reports 15 "
              "participants, mean age ~27.5 years, with a known gender skew toward "
              "male participants -- cite the original WESAD paper (Schmidt et al., "
              "2018) directly for exact figures rather than re-deriving them here.")

    print("\n" + "-" * 55)
    print("Class distribution per subject (from extracted features)")
    print("-" * 55)
    try:
        per_subject, overall = class_distribution_from_features()
        print(per_subject.to_string())
        print("\nOverall class balance across all subjects/windows:")
        print(overall.to_string())
        pct = (overall / overall.sum() * 100).round(1)
        print("\nAs percentages:")
        print(pct.to_string())

        per_subject.to_csv(os.path.join(OUT_DIR, "class_distribution_per_subject.csv"))
        print(f"\nSaved to {OUT_DIR}/class_distribution_per_subject.csv")

        imbalance_ratio = overall.max() / overall.min()
        print(f"\nClass imbalance ratio (largest class / smallest class): {imbalance_ratio:.2f}")
        if imbalance_ratio > 1.5:
            print("This is a meaningful imbalance worth naming explicitly in Limitations --")
            print("it is the reason class-weighting/macro-F1 was used throughout evaluation.")
    except FileNotFoundError:
        print(f"Could not find {FEATURES_PATH} -- run extract_features.py first.")


if __name__ == "__main__":
    main()
