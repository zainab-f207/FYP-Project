"""
Test script for route safety analysis
Tests the RouteSafetyAnalyzer with various scenarios
"""

import sys
from datetime import datetime
from app.services.route_safety_analyzer import RouteSafetyAnalyzer


def test_high_crime_area():
    """Test safety analysis with high crime data"""
    print("\n" + "="*60)
    print("TEST 1: High Crime Area")
    print("="*60)
    
    analyzer = RouteSafetyAnalyzer()
    
    # Simulate high crime data
    crime_data = [
        {"risk_level": "High", "crime_type": "Robbery"},
        {"risk_level": "High", "crime_type": "Assault"},
        {"risk_level": "Medium", "crime_type": "Theft"},
        {"risk_level": "Medium", "crime_type": "Burglary"},
        {"risk_level": "Low", "crime_type": "Vandalism"},
    ]
    
    infrastructure_data = {
        "nearest_police_distance": 1500,
        "nearest_hospital_distance": 2000,
        "has_lighting": True,
        "road_type": "secondary",
        "traffic_level": "moderate"
    }
    
    route_points = [(40.7128, -74.0060), (40.7580, -73.9855)]
    
    result = analyzer.calculate_safety_score(
        route_points=route_points,
        crime_data=crime_data,
        infrastructure_data=infrastructure_data,
        route_distance=5.0,
        route_duration=15
    )
    
    print(f"Overall Score: {result['overall_score']}")
    print(f"Safety Level: {result['safety_level']}")
    print(f"Factors: {result['factors']}")
    print(f"Alerts: {len(result['alerts'])} alert(s)")
    for alert in result['alerts']:
        print(f"  - {alert['type']}: {alert['description']}")
    
    assert result['overall_score'] < 70, "High crime area should have low score"
    assert result['safety_level'] == 'low', "High crime area should be low safety"
    print("✅ TEST PASSED")


def test_safe_area():
    """Test safety analysis with minimal crime data"""
    print("\n" + "="*60)
    print("TEST 2: Safe Area")
    print("="*60)
    
    analyzer = RouteSafetyAnalyzer()
    
    # Minimal crime data
    crime_data = [
        {"risk_level": "Low", "crime_type": "Vandalism"},
    ]
    
    infrastructure_data = {
        "nearest_police_distance": 300,
        "nearest_hospital_distance": 500,
        "has_lighting": True,
        "road_type": "primary",
        "traffic_level": "high"
    }
    
    route_points = [(40.7128, -74.0060), (40.7580, -73.9855)]
    
    result = analyzer.calculate_safety_score(
        route_points=route_points,
        crime_data=crime_data,
        infrastructure_data=infrastructure_data,
        route_distance=5.0,
        route_duration=15
    )
    
    print(f"Overall Score: {result['overall_score']}")
    print(f"Safety Level: {result['safety_level']}")
    print(f"Factors: {result['factors']}")
    print(f"Alerts: {len(result['alerts'])} alert(s)")
    for alert in result['alerts']:
        print(f"  - {alert['type']}: {alert['description']}")
    
    assert result['overall_score'] >= 80, "Safe area should have high score"
    assert result['safety_level'] == 'high', "Safe area should be high safety"
    print("✅ TEST PASSED")


def test_no_crime_data():
    """Test safety analysis with no crime data"""
    print("\n" + "="*60)
    print("TEST 3: No Crime Data")
    print("="*60)
    
    analyzer = RouteSafetyAnalyzer()
    
    crime_data = []
    
    infrastructure_data = {
        "nearest_police_distance": 1000,
        "nearest_hospital_distance": 1500,
        "has_lighting": True,
        "road_type": "secondary",
        "traffic_level": "moderate"
    }
    
    route_points = [(40.7128, -74.0060), (40.7580, -73.9855)]
    
    result = analyzer.calculate_safety_score(
        route_points=route_points,
        crime_data=crime_data,
        infrastructure_data=infrastructure_data,
        route_distance=5.0,
        route_duration=15
    )
    
    print(f"Overall Score: {result['overall_score']}")
    print(f"Safety Level: {result['safety_level']}")
    print(f"Factors: {result['factors']}")
    print(f"Alerts: {len(result['alerts'])} alert(s)")
    for alert in result['alerts']:
        print(f"  - {alert['type']}: {alert['description']}")
    
    assert result['overall_score'] >= 70, "No crime area should have decent score"
    print("✅ TEST PASSED")


def test_poor_infrastructure():
    """Test safety analysis with poor infrastructure"""
    print("\n" + "="*60)
    print("TEST 4: Poor Infrastructure (Far from services)")
    print("="*60)
    
    analyzer = RouteSafetyAnalyzer()
    
    crime_data = [
        {"risk_level": "Medium", "crime_type": "Theft"},
    ]
    
    infrastructure_data = {
        "nearest_police_distance": 5000,  # Very far
        "nearest_hospital_distance": 8000,  # Very far
        "has_lighting": False,
        "road_type": "residential",
        "traffic_level": "low"
    }
    
    route_points = [(40.7128, -74.0060), (40.7580, -73.9855)]
    
    result = analyzer.calculate_safety_score(
        route_points=route_points,
        crime_data=crime_data,
        infrastructure_data=infrastructure_data,
        route_distance=5.0,
        route_duration=15
    )
    
    print(f"Overall Score: {result['overall_score']}")
    print(f"Safety Level: {result['safety_level']}")
    print(f"Factors: {result['factors']}")
    print(f"Alerts: {len(result['alerts'])} alert(s)")
    for alert in result['alerts']:
        print(f"  - {alert['type']}: {alert['description']}")
    
    assert result['overall_score'] < 80, "Poor infrastructure should lower score"
    print("✅ TEST PASSED")


def test_score_bounds():
    """Test that scores stay within valid bounds"""
    print("\n" + "="*60)
    print("TEST 5: Score Bounds (10-100)")
    print("="*60)
    
    analyzer = RouteSafetyAnalyzer()
    
    # Extreme crime data
    crime_data = [
        {"risk_level": "High", "crime_type": "Robbery"},
        {"risk_level": "High", "crime_type": "Assault"},
        {"risk_level": "High", "crime_type": "Murder"},
        {"risk_level": "High", "crime_type": "Robbery"},
        {"risk_level": "High", "crime_type": "Assault"},
    ]
    
    infrastructure_data = {
        "nearest_police_distance": 10000,
        "nearest_hospital_distance": 15000,
        "has_lighting": False,
        "road_type": "residential",
        "traffic_level": "low"
    }
    
    route_points = [(40.7128, -74.0060), (40.7580, -73.9855)]
    
    result = analyzer.calculate_safety_score(
        route_points=route_points,
        crime_data=crime_data,
        infrastructure_data=infrastructure_data,
        route_distance=50.0,
        route_duration=120
    )
    
    print(f"Overall Score: {result['overall_score']}")
    print(f"Safety Level: {result['safety_level']}")
    
    assert 10 <= result['overall_score'] <= 100, "Score must be between 10-100"
    print("✅ TEST PASSED - Score is within valid bounds")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ROUTE SAFETY ANALYZER TEST SUITE")
    print("="*60)
    
    try:
        test_high_crime_area()
        test_safe_area()
        test_no_crime_data()
        test_poor_infrastructure()
        test_score_bounds()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

