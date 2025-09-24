import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def load_severity_map(config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'severity_map.json')
    """Load the manual severity mapping"""
    with open(config_path, 'r') as f:
        data = json.load(f)
        return {k.lower(): v for k, v in data.items()}

def calculate_auto_severity(df):
    """Calculate automated severity scores based on crime frequency"""
    crime_type_freq = df['crime_type'].value_counts()
    
    # Avoid division by zero for new crime types
    crime_type_freq = crime_type_freq.replace(0, 1)
    
    rarity_series = 1 / crime_type_freq
    scaler = MinMaxScaler(feature_range=(2, 10))
    
    auto_severity_map = pd.Series(
        scaler.fit_transform(rarity_series.values.reshape(-1, 1)).flatten(),
        index=rarity_series.index.str.lower()
    ).to_dict()
    
    return auto_severity_map

def get_combined_severity_map(df, manual_map):
    """Combine manual and automated severity maps"""
    auto_map = calculate_auto_severity(df)
    # Manual values override auto values
    combined_map = {**auto_map, **manual_map}
    return combined_map

def engineer_features(df, combined_severity_map=None, df_full=None):
    """Create all features from raw data"""
    df = df.copy()

    if combined_severity_map is None:
        # Load manual severity map
        manual_severity_map = load_severity_map()

        # Create combined severity mapping
        combined_severity_map = get_combined_severity_map(df if df_full is None else df_full, manual_severity_map)

    # Apply severity score with fallback
    median_sev = np.median(list(combined_severity_map.values()))
    df['crime_severity'] = df['crime_type'].str.lower().map(combined_severity_map).fillna(median_sev)

    # Extract temporal features
    df['crime_date'] = pd.to_datetime(df['crime_date'])
    df['hour'] = df['crime_date'].dt.hour
    df['day_of_week'] = df['crime_date'].dt.dayofweek
    df['month'] = df['crime_date'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    # Calculate area crime frequency (spatial feature) from full data if available
    freq_df = df_full if df_full is not None else df
    area_frequency = freq_df['area'].value_counts().to_dict()
    df['area_crime_frequency'] = df['area'].map(area_frequency).fillna(0)

    # Select final features for model
    feature_columns = [
        'crime_severity',
        'hour',
        'day_of_week',
        'is_weekend',
        'area_crime_frequency',
        'latitude',
        'longitude'
    ]

    return df[feature_columns], df

def interpret_clusters(df_with_clusters):
    """Improved cluster interpretation with hybrid risk scoring"""
    # Get cluster statistics
    cluster_stats = df_with_clusters.groupby('cluster').agg({
        'crime_severity': ['mean', 'std', 'min', 'max'],
        'hour': 'mean',
        'area_crime_frequency': 'mean',
        'is_weekend': 'mean'
    }).round(3)

    # Flatten column names
    cluster_stats.columns = ['severity_mean', 'severity_std', 'severity_min', 'severity_max',
                           'hour_mean', 'area_freq_mean', 'weekend_mean']
    cluster_stats = cluster_stats.reset_index()

    # Calculate cluster risk scores (weighted combination of factors)
    cluster_stats['risk_score'] = (
        cluster_stats['severity_mean'] * 1.0 +  # 100% weight on severity
        cluster_stats['area_freq_mean'] * 0.0 +  # 0% weight on area frequency
        cluster_stats['weekend_mean'] * 0.0 +   # 0% weight on weekend factor
        (24 - cluster_stats['hour_mean']) * 0.0  # 0% weight on time (later hours = higher risk)
    )

    # Sort clusters by risk score
    cluster_stats = cluster_stats.sort_values('risk_score', ascending=False)

    # Create risk mapping based on risk scores
    risk_mapping = {}
    n_clusters = len(cluster_stats)

    if n_clusters >= 3:
        # High: top 1/3, Low: bottom 1/3, Medium: middle
        high_count = max(1, n_clusters // 3)
        low_count = max(1, n_clusters // 3)

        for i, row in cluster_stats.iterrows():
            cluster_id = row['cluster']
            if i < high_count:
                risk_mapping[cluster_id] = 'high'
            elif i >= n_clusters - low_count:
                risk_mapping[cluster_id] = 'low'
            else:
                risk_mapping[cluster_id] = 'medium'
    elif n_clusters == 2:
        risk_mapping[cluster_stats.iloc[0]['cluster']] = 'high'
        risk_mapping[cluster_stats.iloc[1]['cluster']] = 'low'
    else:
        risk_mapping[cluster_stats.iloc[0]['cluster']] = 'medium'

    return risk_mapping

def assign_individual_risk_levels(df_with_clusters, risk_mapping):
    """Assign final risk levels with individual crime consideration"""
    df_result = df_with_clusters.copy()

    # Capitalize risk mapping values to match DB ENUM
    capitalized_risk_mapping = {k: v.capitalize() for k, v in risk_mapping.items()}

    # First, assign cluster-based risk
    df_result['cluster_risk'] = df_result['cluster'].map(capitalized_risk_mapping)

    # Initialize final_risk column as string
    df_result['final_risk'] = df_result['cluster_risk'].astype(str)

    # Override for high-severity crimes in low/medium clusters
    high_severity_threshold = 8.0  # Crimes with severity >= 8 are always high risk
    df_result.loc[
        (df_result['crime_severity'] >= high_severity_threshold) &
        (df_result['cluster_risk'].isin(['Low', 'Medium'])),
        'final_risk'
    ] = 'High'

    return df_result

def save_model(model, scaler, filepath=None):
    """Save trained model and scaler"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(filepath, exist_ok=True)
    joblib.dump(model, os.path.join(filepath, 'kmeans_model.pkl'))
    joblib.dump(scaler, os.path.join(filepath, 'scaler.pkl'))

def save_risk_mapping(risk_mapping, filepath=None):
    """Save the risk mapping dictionary"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(filepath, exist_ok=True)
    with open(os.path.join(filepath, 'risk_mapping.json'), 'w') as f:
        json.dump(risk_mapping, f)

def load_risk_mapping(filepath=None):
    """Load the risk mapping dictionary"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')
    with open(os.path.join(filepath, 'risk_mapping.json'), 'r') as f:
        data = json.load(f)
        # Convert string keys to int for proper mapping, handling float strings like '2.0'
        return {int(float(k)): v for k, v in data.items()}
    
def load_model(filepath=None):
    """Load trained model and scaler"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), '..', 'models')
    model = joblib.load(os.path.join(filepath, 'kmeans_model.pkl'))
    scaler = joblib.load(os.path.join(filepath, 'scaler.pkl'))
    return model, scaler

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "hafsa555"),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

def get_db_connection():
    """Create a new DB connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        else:
            raise Exception("Failed to connect to database")
    except Error as e:
        raise Exception(f"Database connection failed: {e}")

def load_crimes_from_db():
    """Load all crimes from database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, area, crime_type, crime_date, latitude, longitude, risk_level
            FROM crimes
            ORDER BY id
        """)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        return df
    except Exception as e:
        raise Exception(f"Failed to load crimes from database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def update_risk_levels_in_db(risk_updates):
    """Update risk_level for multiple crimes in database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_query = "UPDATE crimes SET risk_level = %s WHERE id = %s"
        cursor.executemany(update_query, risk_updates)
        conn.commit()
        print(f"Updated {cursor.rowcount} records in database")
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Failed to update risk levels in database: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def update_new_crimes_risk():
    """Update risk_level for new crimes that have dummy 'medium' risk_level"""
    try:
        # Load crimes with dummy risk_level
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, area, crime_type, crime_date, latitude, longitude
            FROM crimes
            WHERE risk_level = 'Medium' OR risk_level IS NULL
            ORDER BY id
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("No new crimes to update.")
            return

        df_new = pd.DataFrame(rows)

        # Load full crimes data to calculate proper severity mapping
        df_full = load_crimes_from_db()
        manual_severity_map = load_severity_map()
        combined_severity_map = get_combined_severity_map(df_full, manual_severity_map)

        # Predict risk for new crimes
        print(f"Predicting risk for {len(df_new)} new crimes...")
        model, scaler = load_model()
        X_new, df_processed = engineer_features(df_new, combined_severity_map)
        X_new_scaled = scaler.transform(X_new)
        new_clusters = model.predict(X_new_scaled)
        df_processed['cluster'] = new_clusters
        risk_mapping = interpret_clusters(df_processed)
        df_processed['predicted_risk'] = df_processed['cluster'].map(risk_mapping)

        # Apply individual risk level overrides
        df_processed = assign_individual_risk_levels(df_processed, risk_mapping)

        # Update database
        risk_updates = list(zip(df_processed['final_risk'], df_processed['id']))
        update_risk_levels_in_db(risk_updates)
        print("New crimes risk levels updated successfully!")

    except Exception as e:
        raise Exception(f"Failed to update new crimes: {e}")
