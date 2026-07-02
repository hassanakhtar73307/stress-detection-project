\# Project Progress Log



\## Week 0 — Setup

\- Created project structure, GitHub repo, Python environment

\- Installed: pandas, numpy, scipy, scikit-learn, xgboost, tensorflow, keras-tuner, flask, joblib

\- Downloaded and extracted WESAD dataset (15 subjects, S2-S17 excluding S1/S12)



\## Week 1 — Data Loading

\- Wrote src/load\_wesad.py to load pickled subject data

\- Verified subject S2 loads correctly: chest signals (ACC, ECG, EMG, EDA, Temp, Resp), wrist signals (ACC, BVP, EDA, TEMP)

\- Label array confirmed matching signal length (4,255,300 samples at 700Hz)

\- Next: exploratory plot of signals by label (baseline/stress/amusement)

