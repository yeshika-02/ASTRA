"""Metadata-only baselines on ASTRA's frozen split (no light curves used)."""
import sqlite3, sys, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
db = sys.argv[1]
c = sqlite3.connect(db)
rows = c.execute("select split, astra_class, cadence_type, n_sectors, period_source, period, variability_amplitude, snr_estimate from stars").fetchall()
classes = sorted({r[1] for r in rows})
def feats(r, kind):
    cad = 1.0 if r[2] == 'short' else 0.0
    bls = 1.0 if r[4] == 'BLS' else 0.0
    if kind == 'shortcut':  # pipeline artefacts only, no astrophysics
        return [cad, r[3], bls]
    if kind == 'shortcut_no_source':
        return [cad, r[3]]
    if kind == 'physical':  # period + amplitude + snr
        return [np.log10(r[5]), np.log10(max(r[6], 1e-6)), np.log10(max(r[7], 1e-3))]
    return [cad, r[3], bls, np.log10(r[5]), np.log10(max(r[6], 1e-6)), np.log10(max(r[7], 1e-3))]
for kind in ['shortcut_no_source', 'shortcut', 'physical', 'all']:
    X = {s: np.array([feats(r, kind) for r in rows if r[0] == s]) for s in ['train', 'val', 'test']}
    y = {s: np.array([classes.index(r[1]) for r in rows if r[0] == s]) for s in ['train', 'val', 'test']}
    for name, m in [('LogReg', LogisticRegression(max_iter=5000)), ('RandomForest', RandomForestClassifier(n_estimators=500, random_state=42, min_samples_leaf=2))]:
        m.fit(np.vstack([X['train']]), y['train'])
        p = m.predict(X['test'])
        print(f"{kind:20s} {name:12s} test acc={accuracy_score(y['test'], p):.4f} macroF1={f1_score(y['test'], p, average='macro'):.4f}")
