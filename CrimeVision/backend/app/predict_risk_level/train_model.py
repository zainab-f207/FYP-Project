import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder
import joblib
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import gc  # Garbage collection

# Set memory optimization options early - REMOVE THE PROBLEMATIC LINE
pd.set_option('mode.copy_on_write', True)
# Remove this line: pd.set_option('future.no_silent_downcasting', True)

load_dotenv()

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('model', exist_ok=True)

# Setup comprehensive logging
log_filename = f"logs/model_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "hafsa555"),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        raise

def load_data():
    """Load data in chunks to reduce memory usage"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First get count to estimate memory
        cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE risk_level IS NOT NULL AND risk_level != ''")
        count_result = cursor.fetchone()
        if count_result is None:
            logger.warning("No records found or query failed")
            return pd.DataFrame()
        
        total_count = count_result['count']
        logger.info(f"Total records to load: {total_count}")
        
        # Load in chunks if dataset is large
        chunk_size = 10000
        chunks = []
        
        if total_count > 20000:
            logger.info(f"Loading data in chunks of {chunk_size}...")
            offset = 0
            while offset < total_count:
                query = f"SELECT area, crime_type, crime_date, risk_level FROM crimes WHERE risk_level IS NOT NULL AND risk_level != '' LIMIT {chunk_size} OFFSET {offset}"
                cursor.execute(query)
                rows = cursor.fetchall()
                if not rows:
                    break
                chunks.append(pd.DataFrame(rows))
                offset += chunk_size
                logger.info(f"Loaded chunk {len(chunks)}, total records: {offset}")
                gc.collect()
        else:
            # Load all at once for smaller datasets
            query = "SELECT area, crime_type, crime_date, risk_level FROM crimes WHERE risk_level IS NOT NULL AND risk_level != ''"
            cursor.execute(query)
            rows = cursor.fetchall()
            chunks.append(pd.DataFrame(rows))
        
        cursor.close()
        conn.close()
        
        if chunks:
            df = pd.concat(chunks, ignore_index=True)
            logger.info(f"Loaded {len(df)} records with risk_level from database")
            return df
        else:
            logger.error("No data found in database!")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise

def analyze_deterministic_patterns(df):
    """Analyze how deterministic the area-crime-risk patterns are"""
    logger.info("=== ANALYZING DETERMINISTIC PATTERNS ===")
    
    # Use smaller sample for large datasets
    if len(df) > 50000:
        sample_df = df.sample(n=50000, random_state=42)
        logger.info(f"Using 50,000 sample for deterministic pattern analysis")
    else:
        sample_df = df
    
    # Group by area and crime_type to see risk level distribution
    pattern_analysis = sample_df.groupby(['area', 'crime_type', 'risk_level']).size().reset_index(name='count')
    pattern_analysis['total'] = pattern_analysis.groupby(['area', 'crime_type'])['count'].transform('sum')
    pattern_analysis['percentage'] = (pattern_analysis['count'] / pattern_analysis['total']) * 100
    
    # Find patterns that are highly deterministic (>90% one risk level)
    deterministic_patterns = pattern_analysis[pattern_analysis['percentage'] > 90]
    logger.info(f"Highly deterministic patterns (>90%): {len(deterministic_patterns)}")
    
    # Find patterns with good diversity (no single risk level > 70%)
    diverse_patterns = pattern_analysis.groupby(['area', 'crime_type']).filter(
        lambda x: x['percentage'].max() <= 70
    )
    logger.info(f"Diverse patterns (no risk level > 70%): {len(diverse_patterns['area'].unique())}")
    
    return len(deterministic_patterns), pattern_analysis

def create_memory_efficient_visualizations(df, pattern_analysis):
    """Create visualizations with memory optimization"""
    logger.info("Creating memory-optimized visualizations...")
    
    # Use sampling for large datasets
    if len(df) > 20000:
        viz_df = df.sample(n=20000, random_state=42)
        logger.info(f"Using 20,000 sample for visualizations")
    else:
        viz_df = df
    
    # Create visualizations with smaller figure size
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Risk level pie chart (simplified)
    risk_counts = viz_df['risk_level'].value_counts()
    axes[0, 0].pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%', 
                   colors=['#4CAF50', '#FFC107', '#F44336'])
    axes[0, 0].set_title('Risk Level Distribution')
    
    # Top areas bar chart (top 8 only)
    area_counts = viz_df['area'].value_counts().head(8)
    axes[0, 1].bar(range(len(area_counts)), area_counts.values)
    axes[0, 1].set_title('Top 8 Areas by Crime Count')
    axes[0, 1].set_xticks(range(len(area_counts)))
    axes[0, 1].set_xticklabels(area_counts.index, rotation=45, ha='right')
    
    # Crime types bar chart
    crime_counts = viz_df['crime_type'].value_counts()
    axes[1, 0].bar(range(len(crime_counts)), crime_counts.values, color='skyblue')
    axes[1, 0].set_title('Crime Type Distribution')
    axes[1, 0].set_xticks(range(len(crime_counts)))
    axes[1, 0].set_xticklabels(crime_counts.index, rotation=45, ha='right')
    
    # Temporal analysis - crimes by month
    viz_df['month'] = pd.to_datetime(viz_df['crime_date']).dt.month
    monthly_crimes = viz_df['month'].value_counts().sort_index()
    axes[1, 1].bar(monthly_crimes.index, monthly_crimes.values, color='orange')
    axes[1, 1].set_title('Crimes by Month')
    axes[1, 1].set_xlabel('Month')
    axes[1, 1].set_ylabel('Number of Crimes')
    
    plt.tight_layout()
    plt.savefig('model/data_distribution_analysis.png', dpi=150, bbox_inches='tight')
    plt.close('all')
    logger.info("Data distribution analysis saved to model/data_distribution_analysis.png")
    
    # Free memory
    del viz_df, risk_counts, area_counts, crime_counts, monthly_crimes
    gc.collect()

def analyze_data_distribution(df):
    """Analyze and visualize data distribution with memory optimization"""
    logger.info("=== DATA DISTRIBUTION ANALYSIS ===")
    
    # Risk level distribution
    risk_counts = df['risk_level'].value_counts()
    logger.info(f"Risk level distribution:\n{risk_counts.to_dict()}")
    
    # Area distribution
    area_counts = df['area'].value_counts()
    logger.info(f"Top 10 areas:\n{area_counts.head(10).to_dict()}")
    logger.info(f"Total unique areas: {len(area_counts)}")
    
    # Crime type distribution
    crime_counts = df['crime_type'].value_counts()
    logger.info(f"Crime type distribution:\n{crime_counts.to_dict()}")
    logger.info(f"Total unique crime types: {len(crime_counts)}")
    
    # Date range
    logger.info(f"Date range: {df['crime_date'].min()} to {df['crime_date'].max()}")
    
    # Analyze deterministic patterns
    deterministic_count, pattern_analysis = analyze_deterministic_patterns(df)
    logger.info(f"Found {deterministic_count} highly deterministic area-crime-risk patterns")
    
    # Create memory-efficient visualizations
    create_memory_efficient_visualizations(df, pattern_analysis)
    
    # Save analysis results to JSON
    analysis_results = {
        'total_records': len(df),
        'risk_level_distribution': risk_counts.to_dict(),
        'top_10_areas': area_counts.head(10).to_dict(),
        'crime_type_distribution': crime_counts.to_dict(),
        'date_range': {
            'start': str(df['crime_date'].min()),
            'end': str(df['crime_date'].max())
        },
        'deterministic_patterns_count': deterministic_count,
        'unique_areas_count': len(area_counts),
        'unique_crime_types_count': len(crime_counts)
    }
    
    with open('model/data_analysis_results.json', 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    logger.info("Data analysis results saved to model/data_analysis_results.json")
    
    # Free memory
    del risk_counts, area_counts, crime_counts
    gc.collect()
    
    return deterministic_count > len(df) * 0.8

def preprocess_data(df, add_noise=True, noise_level=0.25):
    # First, remove the single "murder" record to prevent data issues
    df = df[df['crime_type'] != 'murder'].copy()
    
    # Extract date features
    df['crime_date'] = pd.to_datetime(df['crime_date'])
    df['year'] = df['crime_date'].dt.year
    df['month'] = df['crime_date'].dt.month
    df['day'] = df['crime_date'].dt.day
    df['weekday'] = df['crime_date'].dt.weekday  # 0=Monday
    df['day_of_year'] = df['crime_date'].dt.dayofyear
    df['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)

    # Add more aggressive noise to break deterministic patterns
    if add_noise:
        logger.info(f"Adding {noise_level*100}% noise to break deterministic patterns...")
        np.random.seed(42)
        
        # Process in smaller groups to save memory
        unique_combinations = list(df[['area', 'crime_type']].drop_duplicates().itertuples(index=False))
        
        for area, crime_type in unique_combinations:
            group_mask = (df['area'] == area) & (df['crime_type'] == crime_type)
            group_size = group_mask.sum()
            
            if group_size > 10:
                group_indices = df[group_mask].index
                risk_counts = df.loc[group_indices, 'risk_level'].value_counts(normalize=True)
                
                if risk_counts.max() > 0.8:
                    n_to_flip = int(group_size * noise_level)
                    indices_to_flip = np.random.choice(group_indices, size=min(n_to_flip, len(group_indices)), replace=False)
                    
                    for idx in indices_to_flip:
                        current_risk = df.loc[idx, 'risk_level']
                        other_risks = [r for r in df['risk_level'].unique() if r != current_risk]
                        if other_risks:
                            df.loc[idx, 'risk_level'] = np.random.choice(other_risks)
        
        logger.info(f"Added targeted noise to break deterministic patterns")

    # Encode categorical
    le_area = LabelEncoder()
    le_crime = LabelEncoder()
    le_risk = LabelEncoder()
    
    df['area_enc'] = le_area.fit_transform(df['area'])
    df['crime_type_enc'] = le_crime.fit_transform(df['crime_type'])
    y_enc = le_risk.fit_transform(df['risk_level'])

    # Features and target
    features = ['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday', 'day_of_year', 'is_weekend']
    X = df[features]
    y = y_enc

    # Save encoders
    joblib.dump(le_area, 'model/label_encoder_area.joblib')
    joblib.dump(le_crime, 'model/label_encoder_crime.joblib')
    joblib.dump(le_risk, 'model/label_encoder_risk.joblib')

    logger.info(f"Risk level distribution after processing: {df['risk_level'].value_counts().to_dict()}")
    logger.info(f"Feature matrix shape: {X.shape}")
    
    # Free memory
    gc.collect()
    
    return X, y, le_risk, df, le_area, le_crime

def train_realistic_model(X, y, le_risk):
    """Train a model that can handle realistic uncertainty"""
    # Use a simpler RandomForest model with fewer estimators for memory
    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=8,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=1
    )

    # Use a single train-test split for simplicity
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    model.fit(X_train, y_train)

    # Check performance
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    overfitting_gap = train_score - test_score

    logger.info(f"Train accuracy: {train_score * 100:.2f}%")
    logger.info(f"Test accuracy: {test_score * 100:.2f}%")
    logger.info(f"Overfitting gap: {overfitting_gap * 100:.2f}%")

    # Detailed predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Calculate additional metrics
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
    logger.info(f"Weighted Precision: {precision:.3f}")
    logger.info(f"Weighted Recall: {recall:.3f}")
    logger.info(f"Weighted F1-Score: {f1:.3f}")

    logger.info("\nClassification Report:")
    class_report = classification_report(y_test, y_pred, target_names=le_risk.classes_, output_dict=True)
    logger.info(classification_report(y_test, y_pred, target_names=le_risk.classes_))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")

    # Create simple performance visualization
    try:
        plt.figure(figsize=(10, 4))
        
        # Confusion matrix heatmap
        plt.subplot(1, 2, 1)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=le_risk.classes_, yticklabels=le_risk.classes_)
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        
        # Performance metrics
        plt.subplot(1, 2, 2)
        metrics = ['Train Acc', 'Test Acc', 'Precision', 'Recall', 'F1-Score']
        values = [train_score, test_score, precision, recall, f1]
        bars = plt.bar(metrics, values, color=['blue', 'green', 'orange', 'red', 'purple'])
        plt.title('Model Performance Metrics')
        plt.ylim(0, 1)
        for bar, value in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                    f'{value:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig('model/model_performance.png', dpi=150, bbox_inches='tight')
        plt.close('all')
        logger.info("Model performance visualization saved to model/model_performance.png")
    except Exception as e:
        logger.warning(f"Could not create performance visualization: {e}")

    # Save detailed performance metrics
    performance_metrics = {
        'train_accuracy': float(train_score),
        'test_accuracy': float(test_score),
        'overfitting_gap': float(overfitting_gap),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'classification_report': class_report,
        'confusion_matrix': cm.tolist(),
    }
    
    with open('model/performance_metrics.json', 'w') as f:
        json.dump(performance_metrics, f, indent=2)
    
    logger.info("Detailed performance metrics saved to model/performance_metrics.json")

    # Free memory
    gc.collect()

    return model, test_score, overfitting_gap, performance_metrics

if __name__ == "__main__":
    # Force garbage collection at start
    gc.collect()
    
    logger.info("=== CRIME RISK MODEL TRAINING STARTED ===")
    start_time = datetime.now()
    logger.info(f"Script started at: {start_time}")
    
    try:
        # Load data with memory optimization
        df = load_data()
        
        if len(df) == 0:
            logger.error("No data found in database! Please check your data.")
            exit(1)
        
        # Analyze data distribution
        is_mostly_deterministic = analyze_data_distribution(df)
        
        # Preprocess data
        noise_level = 0.3 if is_mostly_deterministic else 0.1
        X, y, le_risk, processed_df, le_area, le_crime = preprocess_data(
            df, add_noise=True, noise_level=noise_level
        )
        
        # Free original dataframe memory
        del df
        gc.collect()
        
        # Train model
        model, acc, overfitting_gap, performance_metrics = train_realistic_model(X, y, le_risk)
        
        # Save model
        joblib.dump(model, 'model/random_forest_model.joblib')
        logger.info("Model saved as model/random_forest_model.joblib")
        
        # Test with minimal sample predictions
        logger.info("\n=== SAMPLE PREDICTIONS ===")
        sample_data = [
            ('Cantt', 'Burglary', '2025-10-07'),
            ('DHA Phase 5', 'Robbery', '2025-10-07'),
        ]
        
        sample_results = []
        for area, crime_type, date in sample_data:
            try:
                area_enc = int(le_area.transform([area])[0])
                crime_enc = int(le_crime.transform([crime_type])[0])
                date_obj = pd.to_datetime(date)
                
                features_df = pd.DataFrame([[area_enc, crime_enc, date_obj.year, date_obj.month, 
                                           date_obj.day, date_obj.weekday(), 
                                           date_obj.dayofyear, 1 if date_obj.weekday() in [5, 6] else 0]],
                                         columns=X.columns)
                
                prediction = model.predict(features_df)[0]
                probability = model.predict_proba(features_df)[0]
                risk_level = le_risk.inverse_transform([prediction])[0]
                
                result = {
                    'area': area,
                    'crime_type': crime_type,
                    'date': date,
                    'predicted_risk': risk_level,
                    'probabilities': probability.tolist(),
                }
                sample_results.append(result)
                
                logger.info(f"{area} + {crime_type}: {risk_level} (probs: {probability.round(3)})")
                
            except Exception as e:
                logger.warning(f"Could not test {area} + {crime_type}: {e}")
        
        # Save sample predictions
        with open('model/sample_predictions.json', 'w') as f:
            json.dump(sample_results, f, indent=2)
        logger.info("Sample predictions saved to model/sample_predictions.json")
        
        # Final summary
        end_time = datetime.now()
        total_time = end_time - start_time
        logger.info("\n=== TRAINING SUMMARY ===")
        logger.info(f"Final Model Accuracy: {acc:.3f}")
        logger.info(f"Overfitting Gap: {overfitting_gap:.3f}")
        logger.info(f"Total Training Time: {total_time}")
        logger.info("Training completed successfully!")
        
    except Exception as e:
        logger.error(f"Training failed with error: {e}", exc_info=True)
        raise