import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from utils.helpers import engineer_features, interpret_clusters, assign_individual_risk_levels, save_model, save_risk_mapping, load_crimes_from_db, update_risk_levels_in_db
import os
import numpy as np

def train_crime_risk_model():
    """Main training function that loads from database and updates risk levels"""
    
    # Load data from database
    print("Loading data from database...")
    df = load_crimes_from_db()
    
    # Engineer features
    print("Engineering features...")
    X, df_processed = engineer_features(df)
    
    # Scale features
    print("Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train K-Means model
    print("Training model...")
    kmeans = MiniBatchKMeans(n_clusters=3, random_state=42, batch_size=1000)
    clusters = kmeans.fit_predict(X_scaled)
    
    # Add clusters to processed dataframe
    df_processed['cluster'] = clusters
    
    # Interpret clusters and assign risk labels
    print("Interpreting clusters...")
    risk_mapping = interpret_clusters(df_processed)
    print(f"Risk mapping: {risk_mapping}")
    save_risk_mapping(risk_mapping)
    print("Risk mapping saved!")
    df_processed['predicted_risk'] = df_processed['cluster'].map(risk_mapping)

    # Apply individual risk level overrides
    df_processed = assign_individual_risk_levels(df_processed, risk_mapping)

    # Update risk levels in database
    print("Updating risk levels in database...")
    risk_updates = list(zip(df_processed['final_risk'], df_processed['id']))
    update_risk_levels_in_db(risk_updates)
    print("Database updated successfully!")

    # Save model and scaler for future predictions
    save_model(kmeans, scaler)
    print("Model saved successfully!")

    # Show cluster summary
    cluster_summary = df_processed.groupby('final_risk')[
        ['crime_severity', 'area_crime_frequency']
    ].mean()
    print("\nCluster Summary:")
    print(cluster_summary)

    return df_processed

if __name__ == "__main__":
    # First, export your database data to CSV or connect directly
    # For now, we'll assume you have a CSV file
    
    # Create sample data if no file exists (for testing)
    if not os.path.exists('data/raw_data.csv'):
        os.makedirs('data', exist_ok=True)
        sample_data = {
            'id': range(100),
            'crime_date': pd.date_range('2023-01-01', periods=100, freq='D').strftime('%Y-%m-%d'),
            'area': ['North']*40 + ['South']*35 + ['East']*25,
            'crime_type': ['theft']*30 + ['assault']*25 + ['burglary']*20 + ['vandalism']*15 + ['robbery']*10,
            'latitude': np.random.uniform(40.7, 40.8, 100),
            'longitude': np.random.uniform(-74.0, -73.9, 100),
            'risk_level': ['medium']*100
        }
        df_sample = pd.DataFrame(sample_data)
        df_sample.to_csv('data/raw_data.csv', index=False)
        print("Sample data created for testing.")
    
    # Train the model
    result_df = train_crime_risk_model()