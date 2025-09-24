import pandas as pd
from utils.helpers import engineer_features, load_model, interpret_clusters
import numpy as np

def predict_new_crimes(new_crimes_data):
    """Predict risk level for new crimes"""
    
    # Load trained model and scaler
    print("Loading trained model...")
    model, scaler = load_model()
    
    # If single crime, convert to dataframe
    if isinstance(new_crimes_data, dict):
        new_crimes_data = pd.DataFrame([new_crimes_data])
    
    # Engineer features for new data
    print("Engineering features for new data...")
    X_new, df_processed = engineer_features(new_crimes_data)
    
    # Scale features using the same scaler
    X_new_scaled = scaler.transform(X_new)
    
    # Predict clusters
    print("Predicting risk...")
    new_clusters = model.predict(X_new_scaled)
    df_processed['cluster'] = new_clusters
    
    # Load interpretation from training (you might want to save this too)
    # For simplicity, we'll use the interpret function again
    risk_mapping = interpret_clusters(df_processed)
    df_processed['predicted_risk'] = df_processed['cluster'].map(risk_mapping)
    
    return df_processed

# Example usage
if __name__ == "__main__":
    # Example new crime data
    new_crime = {
        'id': [101],
        'crime_date': ['2024-01-15 14:30:00'],
        'area': ['North'],
        'crime_type': ['burglary'],  # Try with a new crime type like 'cybercrime' to test
        'latitude': [40.75],
        'longitude': [-73.95],
        'risk_level': ['medium']
    }
    
    result = predict_new_crimes(new_crime)
    print(f"\nPredicted Risk: {result['predicted_risk'].iloc[0]}")
    print(f"Assigned Cluster: {result['cluster'].iloc[0]}")