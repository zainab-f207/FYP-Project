"""
AI-Powered Route Safety Analysis Service
Uses Random Forest model for point-based predictions and route aggregation
"""

from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime
import logging
import pandas as pd
import joblib
import os
from app.core.config import MODEL_DIR

logger = logging.getLogger(__name__)


class AIRouteSafetyAnalyzer:
    """Analyzes route safety using Poisson model (primary) + Random Forest (fallback)"""
    
    def __init__(self):
        """Initialize the AI analyzer with loaded model and encoders"""
        self.model = None
        self.le_area = None
        self.le_crime = None
        self.le_risk = None
        self.model_loaded = False
        # Poisson model — set via set_poisson() after construction
        self._poisson_artifacts = None
        self._poisson_predict_fn = None
        
        self._load_model()
        self.current_hour = datetime.now().hour
        self.is_night = self.current_hour >= 20 or self.current_hour < 6

    def set_poisson(self, artifacts, predict_fn):
        """Provide Poisson artifacts so this analyzer uses the new model as primary."""
        self._poisson_artifacts = artifacts
        self._poisson_predict_fn = predict_fn
        logger.info("✅ AIRouteSafetyAnalyzer: Poisson model attached as primary predictor")
    
    def _load_model(self):
        """Load the Random Forest model and encoders"""
        try:
            self.model = joblib.load(os.path.join(MODEL_DIR, 'random_forest_model.joblib'))
            self.le_area = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_area.joblib'))
            self.le_crime = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_crime.joblib'))
            self.le_risk = joblib.load(os.path.join(MODEL_DIR, 'label_encoder_risk.joblib'))
            self.model_loaded = True
            logger.info("✅ AI model and encoders loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading AI model: {e}")
            self.model_loaded = False
    
    def predict_point_risk(
        self,
        area: str,
        crime_type: str,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict risk level for a specific point using AI model
        
        Args:
            area: Area name
            crime_type: Type of crime
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Dict with risk_level, risk_percentage, confidence
        """
        # ── Poisson primary path ────────────────────────────────────────────
        if self._poisson_artifacts and self._poisson_predict_fn and crime_type and crime_type != "No Crimes Detected":
            try:
                result = self._poisson_predict_fn(
                    self._poisson_artifacts,
                    area=area,
                    crime_type=crime_type,
                    date_str=date or datetime.now().strftime('%Y-%m-%d'),
                )
                logger.info(f"[Poisson] {area} + {crime_type} → {result['risk_level']} ({result['risk_percentage']}%)")
                return {
                    "risk_level":     result["risk_level"],
                    "risk_percentage": result["risk_percentage"],
                    "confidence":     result.get("confidence", 0.8),
                    "is_estimated":   result.get("is_estimated", False),
                }
            except Exception as pe:
                logger.warning(f"⚠️ Poisson prediction failed for {area}/{crime_type}, falling back to RF: {pe}")

        if crime_type == "No Crimes Detected":
            return {"risk_level": "Low", "risk_percentage": 0, "confidence": 1.0, "is_estimated": False}

        # ── Random Forest fallback ───────────────────────────────────────────
        if not self.model_loaded:
            logger.warning("⚠️ Model not loaded, returning default risk")
            return {
                "risk_level": "Low",
                "risk_percentage": 0,
                "confidence": 0.0,
                "is_estimated": True
            }
        
        try:
            # First, check if this area has any crimes in the database
            from app.core.database import get_db_connection
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Try multiple matching strategies
                # 1. Exact match with wildcards
                cursor.execute("""
                    SELECT COUNT(*) as crime_count 
                    FROM crimes 
                    WHERE area LIKE %s
                """, (f"%{area}%",))
                result = cursor.fetchone()
                crime_count = result[0] if result else 0
                
                # 2. If no results, try without spaces (handles "Fateh Garh" vs "Fatehgarh")
                if crime_count == 0:
                    area_no_space = area.replace(" ", "")
                    cursor.execute("""
                        SELECT COUNT(*) as crime_count 
                        FROM crimes 
                        WHERE REPLACE(area, ' ', '') LIKE %s
                    """, (f"%{area_no_space}%",))
                    result = cursor.fetchone()
                    crime_count = result[0] if result else 0
                
                cursor.close()
                conn.close()
                
                # If no crimes in this area, it's 100% safe!
                if crime_count == 0:
                    logger.info(f"✅ {area}: No crimes found - 100% SAFE!")
                    return {
                        "risk_level": "Low",
                        "risk_percentage": 0,
                        "confidence": 1.0,
                        "is_estimated": False
                    }
                else:
                    # Store crime count for density adjustment later
                    self._current_area_crime_count = crime_count
                    logger.info(f"📊 {area}: {crime_count} crimes found in database")
                    
            except Exception as db_error:
                logger.warning(f"⚠️ Database check failed: {db_error}")

            
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            parsed_date = datetime.strptime(date, '%Y-%m-%d')
            year = int(parsed_date.year)
            month = int(parsed_date.month)
            day = int(parsed_date.day)
            weekday = int(parsed_date.weekday())
            day_of_year = int(parsed_date.timetuple().tm_yday)
            is_weekend = 1 if weekday in [5, 6] else 0
            
            # Find best match for area and crime type
            matched_area = self._find_best_match(area, self.le_area)
            
            # If crime_type is "No Crimes Detected", we already know it's safe
            if crime_type == "No Crimes Detected":
                return {
                    "risk_level": "Low",
                    "risk_percentage": 0,
                    "confidence": 1.0,
                    "is_estimated": False
                }

            matched_crime = self._find_best_match(crime_type, self.le_crime)
            
            if matched_area is None or matched_crime is None:
                # If area or crime is unknown to AI, but has high crime density in DB, don't mark as SAFE
                if crime_count > 100:
                    risk_percentage = min(80, int(crime_count / 20))
                    risk_level = "High" if risk_percentage > 60 else "Medium"
                    logger.info(f"⚠️ AI fallback for {area}: {crime_count} crimes found, using density-based risk: {risk_percentage}%")
                    return {
                        "risk_level": risk_level,
                        "risk_percentage": risk_percentage,
                        "confidence": 0.5,
                        "is_estimated": True
                    }
                
                logger.warning(f"⚠️ Area '{area}' or crime type '{crime_type}' not found in training data - marking as SAFE")
                return {
                    "risk_level": "Low",
                    "risk_percentage": 0,
                    "confidence": 0.8,
                    "is_estimated": True
                }
            
            # Encode features
            if self.le_area is None or self.le_crime is None:
                logger.error("Label encoders not loaded")
                return {
                    "risk_level": "Medium",
                    "risk_percentage": 50,
                    "confidence": 0.0,
                    "is_estimated": True
                }
            
            area_enc = int(self.le_area.transform([matched_area])[0])
            crime_enc = int(self.le_crime.transform([matched_crime])[0])
            
            # Create feature DataFrame
            features_df = pd.DataFrame(
                [[area_enc, crime_enc, year, month, day, weekday, day_of_year, is_weekend]],
                columns=['area_enc', 'crime_type_enc', 'year', 'month', 'day', 'weekday', 'day_of_year', 'is_weekend']
            ).astype(int)
            
            # Make prediction
            if self.model is None or self.le_risk is None:
                logger.error("Model or risk encoder not loaded")
                return {
                    "risk_level": "Medium",
                    "risk_percentage": 50,
                    "confidence": 0.0,
                    "is_estimated": True
                }
            
            pred = self.model.predict(features_df)[0]
            pred_proba = self.model.predict_proba(features_df)[0]
            risk_level = self.le_risk.inverse_transform([pred])[0]
            confidence = float(max(pred_proba))
            
            # Calculate risk percentage
            risk_percentage = self._calculate_risk_percentage(risk_level, pred_proba)
            
            # --- CRIME DENSITY ADJUSTMENT ---
            # If an area has a very high crime count, boost the risk percentage
            crime_count = getattr(self, '_current_area_crime_count', 0)
            if crime_count > 500:
                # Boost risk for high-crime areas
                boost = min(30, int(crime_count / 100))
                risk_percentage = min(95, risk_percentage + boost)
                if risk_percentage > 60:
                    risk_level = "High"
                elif risk_percentage > 20:
                    risk_level = "Medium"
                logger.info(f"🔥 High crime density boost for {area}: +{boost}% risk")
            
            logger.info(f"✅ Point prediction: {area} + {crime_type} = {risk_level} ({risk_percentage}%)")
            
            return {
                "risk_level": str(risk_level).capitalize(),
                "risk_percentage": risk_percentage,
                "confidence": confidence,
                "is_estimated": False
            }
            
        except Exception as e:
            logger.error(f"❌ Error predicting point risk: {e}")
            return {
                "risk_level": "Medium",
                "risk_percentage": 50,
                "confidence": 0.0,
                "is_estimated": True
            }
    
    def analyze_route_with_ai(
        self,
        route_points: List[Tuple[float, float]],
        areas: List[str],
        crime_types: List[str],
        date: Optional[str] = None,
        hour: Optional[int] = None,   # travel hour 0-23; affects night-time risk weighting
    ) -> Dict[str, Any]:
        """
        Analyze entire route using AI predictions for each point
        
        Args:
            route_points: List of (lat, lng) tuples
            areas: List of area names for each point
            crime_types: List of crime types for each point
            date: Date for prediction
            
        Returns:
            Dict with overall_score, safety_level, point_predictions, alerts
        """
        # Proceed if either Poisson (primary) or Random Forest (fallback) is available
        if not self.model_loaded and not self._poisson_artifacts:
            logger.warning("⚠️ No model loaded, cannot perform AI analysis")
            return self._get_default_analysis()
        
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            point_predictions = []
            risk_percentages = []
            high_risk_count = 0
            medium_risk_count = 0
            
            # Predict risk for each point
            for i, (lat, lng) in enumerate(route_points):
                area = areas[i] if i < len(areas) else "Unknown"
                crime_type = crime_types[i] if i < len(crime_types) else "Unknown"
                
                prediction = self.predict_point_risk(area, crime_type, date)
                point_predictions.append({
                    "point_index": i,
                    "latitude": lat,
                    "longitude": lng,
                    "area": area,
                    "crime_type": crime_type,
                    "prediction": prediction
                })
                
                risk_percentages.append(prediction["risk_percentage"])
                
                if prediction["risk_level"] == "High":
                    high_risk_count += 1
                elif prediction["risk_level"] == "Medium":
                    medium_risk_count += 1
            
            # Calculate overall route safety score
            # Weight: 70% average risk + 30% worst hotspot so routes with even one
            # high-risk area are naturally penalised more than uniformly moderate routes.
            if risk_percentages:
                avg_risk = sum(risk_percentages) / len(risk_percentages)
                max_risk = max(risk_percentages)
                overall_risk_percentage = (avg_risk * 0.7) + (max_risk * 0.3)
                overall_score = 100 - overall_risk_percentage
            else:
                overall_score = 70.0

            # Apply nighttime adjustment using travel hour when provided
            is_night = (hour >= 20 or hour < 6) if hour is not None else self.is_night
            if is_night:
                overall_score *= 0.85
            
            overall_score = max(10, min(100, overall_score))
            
            # Determine safety level
            if overall_score >= 80:
                safety_level = "high"
            elif overall_score >= 60:
                safety_level = "medium"
            else:
                safety_level = "low"
            
            # Generate alerts
            alerts = self._generate_ai_alerts(high_risk_count, medium_risk_count, overall_score, is_night=is_night)
            
            logger.info(f"✅ Route AI analysis complete: Score={overall_score:.1f}, Level={safety_level}")
            
            return {
                "overall_score": round(overall_score, 1),
                "safety_level": safety_level,
                "point_predictions": point_predictions,
                "alerts": alerts,
                "summary": {
                    "total_points": len(route_points),
                    "high_risk_points": high_risk_count,
                    "medium_risk_points": medium_risk_count,
                    "average_risk_percentage": round(sum(risk_percentages) / len(risk_percentages), 1) if risk_percentages else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in route AI analysis: {e}")
            return self._get_default_analysis()
    
    def _find_best_match(self, value: str, encoder) -> Optional[str]:
        """Find best matching value in encoder classes with fuzzy matching"""
        try:
            if not value or not encoder:
                return None
                
            classes = encoder.classes_
            if value in classes:
                return value
            
            # 1. Try case-insensitive and stripped match
            value_clean = value.lower().strip()
            for cls in classes:
                if cls.lower().strip() == value_clean:
                    return cls
            
            # 2. Try matching without spaces (handles "Fateh Garh" vs "Fatehgarh")
            value_no_space = value_clean.replace(" ", "")
            for cls in classes:
                if cls.lower().replace(" ", "") == value_no_space:
                    return cls
                    
            # 3. Try partial matches (ONLY if it's a very strong match)
            for cls in classes:
                cls_lower = cls.lower().strip()
                # Check if one is a major part of the other (at least 70% length)
                if value_clean in cls_lower or cls_lower in value_clean:
                    longer = max(len(value_clean), len(cls_lower))
                    shorter = min(len(value_clean), len(cls_lower))
                    if shorter / longer >= 0.7:
                        return cls
            
            return None
        except Exception as e:
            logger.warning(f"Error finding best match for '{value}': {e}")
            return None
    
    def _calculate_risk_percentage(self, risk_level: str, probabilities: List[float]) -> int:
        """Calculate risk percentage from probabilities"""
        try:
            if self.le_risk is None:
                logger.warning("Risk encoder not loaded")
                return 50
            
            risk_level_str = str(risk_level).lower()
            risk_index = None
            
            for i, cls in enumerate(self.le_risk.classes_):
                if cls.lower() == risk_level_str:
                    risk_index = i
                    break
            
            if risk_index is not None and risk_index < len(probabilities):
                return int(probabilities[risk_index] * 100)
            
            return 50
        except Exception as e:
            logger.warning(f"Error calculating risk percentage: {e}")
            return 50
    
    def _generate_ai_alerts(self, high_risk_count: int, medium_risk_count: int, score: float, is_night: bool = None) -> List[Dict]:
        """Generate alerts based on AI predictions"""
        alerts = []
        
        if high_risk_count > 0:
            alerts.append({
                "type": "⚠️ High Risk Alert",
                "description": f"AI has identified {high_risk_count} critical risk zones. These areas have high historical crime density and AI predicts a high probability of incidents.",
                "severity": "high",
                "location": "Specific segments"
            })
            
            if high_risk_count >= 3:
                alerts.append({
                    "type": "🚫 Avoidance Recommended",
                    "description": "This route contains multiple high-risk clusters. AI strongly recommends using a different path or traveling only during peak daylight hours with high visibility.",
                    "severity": "high",
                    "location": "Route clusters"
                })
        
        if medium_risk_count > 0:
            alerts.append({
                "type": "🟡 Caution Advised",
                "description": f"Detected {medium_risk_count} moderate risk points. AI suggests staying alert and avoiding stops in these areas.",
                "severity": "medium",
                "location": "Intermediate segments"
            })
        
        if score < 50:
            alerts.append({
                "type": "🚨 Critical Safety Warning",
                "description": "Overall safety score is critical. AI analysis indicates this route passes through several volatile areas. Ensure your vehicle is secure and do not stop for strangers.",
                "severity": "high",
                "location": "Entire route"
            })
        elif score < 75:
            alerts.append({
                "type": "📋 Safety Protocol",
                "description": "Route is moderately safe. AI recommends keeping doors locked and windows up while passing through identified risk points.",
                "severity": "medium",
                "location": "Entire route"
            })
        
        _is_night = is_night if is_night is not None else self.is_night
        if _is_night:
            alerts.append({
                "type": "🌙 Nighttime Advisory",
                "description": "Nighttime travel detected. Historical crime patterns show higher incident rates after dark, so risk predictions are adjusted accordingly.",
                "severity": "medium",
                "location": "Time-based"
            })
            
        if not alerts:
            alerts.append({
                "type": "✅ Optimal Safety",
                "description": "AI analysis indicates this is an exceptionally safe route with minimal historical incidents detected along the path.",
                "severity": "low",
                "location": "Entire route"
            })
        
        return alerts
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when model is not available"""
        return {
            "overall_score": 70.0,
            "safety_level": "medium",
            "point_predictions": [],
            "alerts": [{
                "type": "Analysis Unavailable",
                "description": "AI model not available. Using default safety assessment.",
                "severity": "low",
                "location": "Entire route"
            }],
            "summary": {
                "total_points": 0,
                "high_risk_points": 0,
                "medium_risk_points": 0,
                "average_risk_percentage": 0
            }
        }

