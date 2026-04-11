"""
Crime Risk Model - Prediction Module
Predict High / Medium / Low risk for new crime records
using the saved Random Forest classifier.
"""

import os, sys, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.helpers import engineer_features, load_model


def predict_new_crimes(new_crimes_data):
    if isinstance(new_crimes_data, dict):
        new_crimes_data = pd.DataFrame([new_crimes_data])
    elif isinstance(new_crimes_data, list):
        new_crimes_data = pd.DataFrame(new_crimes_data)

    df_input = new_crimes_data.copy()
    model, scaler, artifacts = load_model()

    combined_severity_map = artifacts['combined_severity_map']
    area_freq_map         = artifacts['area_freq_map']
    area_freq_median      = artifacts['area_freq_median']

    X_new, df_proc = engineer_features(
        df_input,
        combined_severity_map=combined_severity_map,
        area_freq_map=area_freq_map,
        area_freq_median=area_freq_median,
    )

    X_scaled      = scaler.transform(X_new)
    predictions   = model.predict(X_scaled)
    probabilities = model.predict_proba(X_scaled)
    class_labels  = model.classes_

    df_proc = df_proc.copy()
    df_proc['predicted_risk'] = predictions
    df_proc['risk_probability'] = [
        {cls: round(float(prob), 3) for cls, prob in zip(class_labels, row)}
        for row in probabilities
    ]
    return df_proc


if __name__ == "__main__":
    test_cases = [
        {'id': 101, 'crime_date': '2024-03-15 23:45:00', 'area': 'Wapda Town',
         'crime_type': 'murder', 'latitude': 31.47, 'longitude': 74.29},
        {'id': 102, 'crime_date': '2024-06-10 14:00:00', 'area': 'Bahria Orchard',
         'crime_type': 'theft', 'latitude': 31.41, 'longitude': 74.20},
        {'id': 103, 'crime_date': '2024-11-01 21:30:00', 'area': 'Brand New Area XYZ',
         'crime_type': 'cybercrime', 'latitude': 31.55, 'longitude': 74.35},
    ]
    results = predict_new_crimes(test_cases)
    for _, row in results.iterrows():
        print(f"ID {row.get('id','?')} | {row.get('crime_type','?')} @ {row.get('area','?')} | {row.get('crime_date','?')} -> {row['predicted_risk']}  {row['risk_probability']}")
