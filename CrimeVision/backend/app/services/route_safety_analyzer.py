"""
Route Safety Analysis Service
Comprehensive rule-based safety scoring for navigation routes
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)


class RouteSafetyAnalyzer:
    """Analyzes route safety using rule-based scoring algorithm"""
    
    # Scoring constants
    BASE_SCORE = 100
    
    # Crime-related deductions
    HIGH_CRIME_DEDUCTION = 15
    MEDIUM_CRIME_DEDUCTION = 8
    LOW_CRIME_DEDUCTION = 3
    
    # Infrastructure deductions
    ISOLATED_ROAD_DEDUCTION = 10
    POOR_LIGHTING_DEDUCTION = 12
    FAR_FROM_POLICE_DEDUCTION = 8
    FAR_FROM_HOSPITAL_DEDUCTION = 5
    
    # Infrastructure bonuses
    NEAR_POLICE_BONUS = 10
    NEAR_HOSPITAL_BONUS = 8
    MAIN_ROAD_BONUS = 5
    HIGH_TRAFFIC_BONUS = 5
    GOOD_LIGHTING_BONUS = 8
    
    # Distance thresholds (in meters)
    POLICE_PROXIMITY_THRESHOLD = 500
    HOSPITAL_PROXIMITY_THRESHOLD = 1000
    FAR_POLICE_THRESHOLD = 2000
    FAR_HOSPITAL_THRESHOLD = 3000
    
    # Crime density thresholds
    HIGH_CRIME_THRESHOLD = 5
    MEDIUM_CRIME_THRESHOLD = 2
    
    def __init__(self):
        """Initialize the analyzer"""
        self.current_hour = datetime.now().hour
        self.is_night = self.current_hour >= 20 or self.current_hour < 6
        self.is_late_night = self.current_hour >= 23 or self.current_hour < 5
    
    def calculate_safety_score(
        self,
        route_points: List[Tuple[float, float]],
        crime_data: List[Dict[str, Any]],
        infrastructure_data: Dict[str, Any],
        route_distance: Optional[float] = None,
        route_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive safety score for a route
        
        Args:
            route_points: List of (lat, lng) tuples along the route
            crime_data: Crime incidents near route points
            infrastructure_data: Police stations, hospitals, road types, lighting
            route_distance: Route distance in km
            route_duration: Route duration in minutes
            
        Returns:
            Dict with overall_score, safety_level, factors, and alerts
        """
        score = self.BASE_SCORE
        alerts = []
        factors = {
            "crime_rate": "low",
            "lighting": "good",
            "traffic": "moderate",
            "emergency_services_proximity": "high",
            "road_type": "main_road"
        }
        
        # Analyze crime data
        crime_score, crime_alerts, crime_factors = self._analyze_crime_data(crime_data)
        score -= crime_score
        alerts.extend(crime_alerts)
        factors.update(crime_factors)
        
        # Analyze infrastructure
        infra_score, infra_alerts, infra_factors = self._analyze_infrastructure(
            infrastructure_data,
            route_distance
        )
        score -= infra_score
        alerts.extend(infra_alerts)
        factors.update(infra_factors)
        
        # Apply time-based multipliers
        score = self._apply_time_multipliers(score, crime_score)
        
        # Ensure score is within valid range
        score = max(10, min(100, score))
        
        # Determine safety level
        safety_level = self._get_safety_level(score)
        
        # Add default alert if none exist
        if not alerts:
            alerts.append(self._get_default_alert(score))
        
        return {
            "overall_score": round(score, 1),
            "safety_level": safety_level,
            "alerts": alerts,
            "factors": factors
        }
    
    def _analyze_crime_data(
        self,
        crime_data: List[Dict[str, Any]]
    ) -> Tuple[float, List[Dict], Dict]:
        """Analyze crime data and calculate deductions"""
        score_deduction = 0
        alerts = []
        factors = {"crime_rate": "low"}
        
        if not crime_data:
            return score_deduction, alerts, factors
        
        # Count crimes by severity
        high_crimes = sum(1 for c in crime_data if c.get("risk_level") == "High")
        medium_crimes = sum(1 for c in crime_data if c.get("risk_level") == "Medium")
        low_crimes = sum(1 for c in crime_data if c.get("risk_level") == "Low")
        
        # Calculate deductions
        score_deduction += high_crimes * self.HIGH_CRIME_DEDUCTION
        score_deduction += medium_crimes * self.MEDIUM_CRIME_DEDUCTION
        score_deduction += low_crimes * self.LOW_CRIME_DEDUCTION
        
        # Determine crime rate factor
        total_crimes = len(crime_data)
        if total_crimes >= self.HIGH_CRIME_THRESHOLD:
            factors["crime_rate"] = "high"
        elif total_crimes >= self.MEDIUM_CRIME_THRESHOLD:
            factors["crime_rate"] = "medium"
        
        # Generate crime alerts
        if high_crimes > 0:
            alerts.append({
                "type": "High Crime Area",
                "description": f"{high_crimes} high-risk crimes detected near route",
                "severity": "high",
                "location": "Route segments"
            })
        elif medium_crimes > 0:
            alerts.append({
                "type": "Moderate Crime Activity",
                "description": f"{medium_crimes} crimes detected along route",
                "severity": "medium",
                "location": "Route segments"
            })
        
        return score_deduction, alerts, factors
    
    def _analyze_infrastructure(
        self,
        infrastructure_data: Dict[str, Any],
        route_distance: Optional[float] = None
    ) -> Tuple[float, List[Dict], Dict]:
        """Analyze infrastructure and calculate adjustments"""
        score_adjustment = 0
        alerts = []
        factors = {
            "lighting": "good",
            "traffic": "moderate",
            "emergency_services_proximity": "high",
            "road_type": "main_road"
        }
        
        # Check police proximity
        police_distance = infrastructure_data.get("nearest_police_distance", float('inf'))
        if police_distance < self.POLICE_PROXIMITY_THRESHOLD:
            score_adjustment -= self.NEAR_POLICE_BONUS  # Bonus (negative deduction)
            factors["emergency_services_proximity"] = "very_high"
        elif police_distance > self.FAR_POLICE_THRESHOLD:
            score_adjustment += self.FAR_POLICE_DEDUCTION
            factors["emergency_services_proximity"] = "low"
        
        # Check hospital proximity
        hospital_distance = infrastructure_data.get("nearest_hospital_distance", float('inf'))
        if hospital_distance < self.HOSPITAL_PROXIMITY_THRESHOLD:
            score_adjustment -= self.NEAR_HOSPITAL_BONUS
        elif hospital_distance > self.FAR_HOSPITAL_THRESHOLD:
            score_adjustment += self.FAR_HOSPITAL_DEDUCTION
        
        # Check lighting (nighttime)
        if self.is_night:
            has_lighting = infrastructure_data.get("has_lighting", False)
            if has_lighting:
                score_adjustment -= self.GOOD_LIGHTING_BONUS
                factors["lighting"] = "good"
            else:
                score_adjustment += self.POOR_LIGHTING_DEDUCTION
                factors["lighting"] = "poor"
        
        # Check road type
        road_type = infrastructure_data.get("road_type", "secondary")
        if road_type in ["primary", "motorway"]:
            score_adjustment -= self.MAIN_ROAD_BONUS
            factors["road_type"] = "main_road"
        elif road_type == "residential":
            factors["road_type"] = "residential"
        
        # Check traffic
        traffic_level = infrastructure_data.get("traffic_level", "moderate")
        if traffic_level == "high":
            score_adjustment -= self.HIGH_TRAFFIC_BONUS
            factors["traffic"] = "high"
        
        return score_adjustment, alerts, factors
    
    def _apply_time_multipliers(self, score: float, crime_deduction: float) -> float:
        """Apply time-based multipliers for nighttime"""
        if self.is_late_night and crime_deduction > 0:
            # 2x multiplier after 11 PM
            crime_multiplier = 2.0
        elif self.is_night and crime_deduction > 0:
            # 1.5x multiplier after 8 PM
            crime_multiplier = 1.5
        else:
            crime_multiplier = 1.0
        
        # Recalculate with multiplier
        if crime_multiplier > 1.0:
            additional_deduction = crime_deduction * (crime_multiplier - 1.0)
            score -= additional_deduction
        
        return score
    
    def _get_safety_level(self, score: float) -> str:
        """Determine safety level from score"""
        if score >= 80:
            return "high"
        elif score >= 60:
            return "medium"
        else:
            return "low"
    
    def _get_default_alert(self, score: float) -> Dict[str, str]:
        """Get default alert based on score"""
        if score >= 80:
            return {
                "type": "Safe Route",
                "description": "This route appears to be relatively safe based on available data.",
                "severity": "low",
                "location": "Entire route"
            }
        elif score >= 60:
            return {
                "type": "Moderate Risk",
                "description": "Some safety concerns detected. Stay vigilant.",
                "severity": "medium",
                "location": "Route segments"
            }
        else:
            return {
                "type": "High Risk",
                "description": "Significant safety concerns detected. Consider alternative routes.",
                "severity": "high",
                "location": "Route segments"
            }

