"""
Crime Risk Model - Training Script
====================================
Trains a RandomForestClassifier to predict High / Medium / Low crime risk.

Why Random Forest?
------------------
* Handles mixed numeric/categorical features without heavy preprocessing
* Naturally robust to outliers (ensemble of trees)
* Generalises well to unseen areas / crime types via median fallback
* Produces feature-importance ranking for interpretability
* No re-interpretation step needed for new data -- just call predict()

Pipeline
--------
1. Load crime records from the database
2. Engineer features (severity, temporal, spatial)
3. Generate deterministic rule-based risk labels as training targets
4. Train RandomForestClassifier with class_weight='balanced'
5. Evaluate via stratified 5-fold cross-validation
6. Save model + scaler + artifacts (maps, medians, classes)
7. Update ALL risk_level values in the database with model predictions
"""

import os
import sys
import json
import subprocess
import logging
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report

logger = logging.getLogger(__name__)

# Allow running from the crime_risk_model directory directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helpers import (
    load_severity_map,
    get_combined_severity_map,
    engineer_features,
    compute_risk_labels,
    save_model,
    load_crimes_from_db,
    update_risk_levels_in_db,
)
try:
    from utils.severity_sync import sync_severity_from_db as _sync_severity
except Exception:
    _sync_severity = None
try:
    from utils.poisson_predictor import build_artifacts as _build_poisson, save_artifacts as _save_poisson
except Exception:
    _build_poisson = _save_poisson = None


_LEGACY_TRAIN_SCRIPT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'predict_risk_level', 'train_model.py')
)


def _run_legacy_retrain() -> None:
    """Rebuild the legacy Random Forest fallback as part of the same retrain."""
    legacy_dir = os.path.dirname(_LEGACY_TRAIN_SCRIPT)
    logger.info("Building legacy Random Forest fallback...")
    result = subprocess.run(
        [sys.executable, _LEGACY_TRAIN_SCRIPT],
        capture_output=True,
        text=True,
        cwd=legacy_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Legacy retrain failed (rc=%d): %s" % (
                result.returncode,
                (result.stderr or result.stdout or "")[-2000:],
            )
        )
    logger.info("Legacy Random Forest retrain complete.\n%s", (result.stdout or "")[-1000:])


def train_crime_risk_model():
    """Full training pipeline. Returns the processed DataFrame."""

    # Sync PPC law sections → severity_map.json before training so the
    # model always learns from the latest authenticated severity scores.
    if _sync_severity is not None:
        try:
            summary = _sync_severity()
            print(f"severity_sync: +{summary['added']} added, {summary['updated']} updated")
        except Exception as e:
            print(f"severity_sync warning (non-fatal): {e}")

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    print("Loading data from database...")
    df = load_crimes_from_db()
    print(f"Loaded {len(df)} crime records.")

    if df.empty:
        raise ValueError("No crime records found in the database. Cannot train.")

    # ------------------------------------------------------------------
    # 2. Build severity map (manual + auto-derived)
    # ------------------------------------------------------------------
    print("Building severity map...")
    manual_severity_map   = load_severity_map()
    combined_severity_map = get_combined_severity_map(df, manual_severity_map)

    # ------------------------------------------------------------------
    # 3. Engineer features
    # ------------------------------------------------------------------
    print("Engineering features...")
    X, df_proc = engineer_features(df, combined_severity_map=combined_severity_map)

    # Store area freq map and medians so new-data prediction can reuse them
    raw_counts       = df['area'].value_counts().to_dict()
    total            = max(sum(raw_counts.values()), 1)
    area_freq_map    = {k: v / total for k, v in raw_counts.items()}
    area_freq_median = float(np.median(list(area_freq_map.values())))
    severity_median  = float(np.median(list(combined_severity_map.values())))

    # ------------------------------------------------------------------
    # 4. Generate training labels via rule-based scoring
    # ------------------------------------------------------------------
    print("Generating rule-based training labels...")
    df_labelled = compute_risk_labels(df_proc)
    y = df_labelled['computed_risk']

    label_dist = y.value_counts()
    print(f"Label distribution:\n{label_dist}\n")

    # ------------------------------------------------------------------
    # 5. Scale features
    # ------------------------------------------------------------------
    print("Scaling features...")
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ------------------------------------------------------------------
    # 6. Train Random Forest
    # ------------------------------------------------------------------
    print("Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators  = 200,       # enough trees for stability
        max_depth     = 15,        # prevent overfitting on 50k rows
        min_samples_leaf = 10,     # require at least 10 samples per leaf
        class_weight  = 'balanced',# compensate for label imbalance
        random_state  = 42,
        n_jobs        = -1,        # use all CPU cores
    )
    model.fit(X_scaled, y)

    # ------------------------------------------------------------------
    # 7. Cross-validation evaluation
    # ------------------------------------------------------------------
    print("\nRunning 5-fold cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy', n_jobs=-1)
    print(f"CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
    print(f"Per-fold:    {[round(s, 3) for s in cv_scores]}")

    # Full training-set report
    y_pred = model.predict(X_scaled)
    print("\nClassification Report (training set):")
    print(classification_report(y, y_pred))

    # Feature importance
    feature_cols = X.columns.tolist()
    importances  = model.feature_importances_
    feat_imp     = sorted(zip(feature_cols, importances), key=lambda x: -x[1])
    print("\nFeature Importances:")
    for name, imp in feat_imp:
        bar = '#' * int(imp * 40)
        print(f"  {name:<30} {imp:.4f}  {bar}")

    # ------------------------------------------------------------------
    # 8. Save model + artifacts
    # ------------------------------------------------------------------
    print("\nSaving model, scaler and artifacts...")
    from datetime import datetime as _dt
    artifacts = {
        'combined_severity_map': combined_severity_map,
        'area_freq_map':         area_freq_map,
        'area_freq_median':      area_freq_median,
        'severity_median':       severity_median,
        'label_classes':         model.classes_.tolist(),
        'cv_accuracy_mean':      float(cv_scores.mean()),
        'cv_accuracy_std':       float(cv_scores.std()),
        'n_training_samples':    int(len(df)),
        'trained_at':            _dt.now().isoformat(),
    }
    save_model(model, scaler, artifacts)
    print("Model saved.")

    # ------------------------------------------------------------------
    # 8b. Build and save Poisson probability artifacts
    # ------------------------------------------------------------------
    if _build_poisson and _save_poisson:
        print("Building Poisson probability artifacts...")
        try:
            poisson_art = _build_poisson(df)
            _save_poisson(poisson_art)
            print(
                f"Poisson artifacts saved: "
                f"{len(poisson_art['pair_lambdas'])} area×crime pairs, "
                f"{poisson_art['total_observation_days']} observation days."
            )
        except Exception as _pe:
            print(f"Poisson artifact build warning (non-fatal): {_pe}")
    else:
        print("poisson_predictor module not available — skipping Poisson artifacts.")

    # ------------------------------------------------------------------
    # 8c. Rebuild the legacy RF fallback before DB labels are refreshed.
    # ------------------------------------------------------------------
    try:
        _run_legacy_retrain()
    except Exception as _le:
        print(f"Legacy retrain warning (non-fatal): {_le}")

    # ------------------------------------------------------------------
    # 9. Update database with model predictions
    # ------------------------------------------------------------------
    print("Updating risk levels in database...")
    df_labelled['predicted_risk'] = y_pred
    risk_updates = list(zip(df_labelled['predicted_risk'], df_labelled['id']))
    update_risk_levels_in_db(risk_updates)
    print("Database updated successfully.")

    # Summary
    pred_dist = pd.Series(y_pred).value_counts()
    print(f"\nFinal predicted risk distribution:\n{pred_dist}")

    return df_labelled


if __name__ == "__main__":
    result_df = train_crime_risk_model()
    print("\nTraining complete.")
