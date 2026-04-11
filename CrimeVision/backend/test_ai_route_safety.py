"""
Test suite for AI-powered route safety analysis
Tests the new /api/crimes/analyze-route-safety-ai endpoint
"""

import json
import sys
import os
import requests

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Test against running server
BASE_URL = "http://localhost:8000/api"


class TestAIRouteSafetyAnalysis:
    """Test cases for AI route safety analysis"""
    
    def test_ai_route_safety_endpoint_exists(self):
        """Test that the AI route safety endpoint is accessible"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    },
                    {
                        "latitude": 31.5300,
                        "longitude": 74.3600,
                        "area": "DHA Phase 5",
                        "crime_type": "Robbery"
                    }
                ]
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ AI route safety endpoint is accessible")
    
    def test_ai_route_safety_response_structure(self):
        """Test that response has correct structure"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "overall_score" in data, "Missing overall_score"
        assert "safety_level" in data, "Missing safety_level"
        assert "point_predictions" in data, "Missing point_predictions"
        assert "alerts" in data, "Missing alerts"
        assert "summary" in data, "Missing summary"
        
        # Check types
        assert isinstance(data["overall_score"], (int, float)), "overall_score should be numeric"
        assert isinstance(data["safety_level"], str), "safety_level should be string"
        assert isinstance(data["point_predictions"], list), "point_predictions should be list"
        assert isinstance(data["alerts"], list), "alerts should be list"
        
        print("✅ Response structure is correct")
    
    def test_ai_route_safety_score_range(self):
        """Test that safety score is within valid range (0-100)"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        score = data["overall_score"]
        
        assert 0 <= score <= 100, f"Score {score} is outside valid range [0, 100]"
        print(f"✅ Safety score {score} is within valid range")
    
    def test_ai_route_safety_multiple_points(self):
        """Test analysis with multiple route points"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    },
                    {
                        "latitude": 31.5300,
                        "longitude": 74.3600,
                        "area": "DHA Phase 5",
                        "crime_type": "Robbery"
                    },
                    {
                        "latitude": 31.5400,
                        "longitude": 74.3700,
                        "area": "Gulberg",
                        "crime_type": "Theft"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have predictions for all points
        assert len(data["point_predictions"]) == 3, "Should have 3 point predictions"
        assert data["summary"]["total_points"] == 3, "Summary should show 3 total points"
        
        print(f"✅ Multiple point analysis works correctly")
    
    def test_ai_route_safety_with_date(self):
        """Test analysis with specific date"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    }
                ],
                "date": "2025-10-15"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        
        print("✅ Analysis with specific date works correctly")
    
    def test_ai_route_safety_alerts_generated(self):
        """Test that alerts are generated"""
        response = requests.post(
            f"{BASE_URL}/crimes/analyze-route-safety-ai",
            json={
                "route_points": [
                    {
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "area": "Cantt",
                        "crime_type": "Burglary"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least one alert
        assert len(data["alerts"]) > 0, "Should have at least one alert"
        
        # Check alert structure
        for alert in data["alerts"]:
            assert "type" in alert, "Alert missing type"
            assert "description" in alert, "Alert missing description"
            assert "severity" in alert, "Alert missing severity"
        
        print(f"✅ Alerts generated correctly ({len(data['alerts'])} alerts)")
    
    def test_existing_predict_risk_still_works(self):
        """Test that existing predict-risk endpoint still works"""
        response = requests.post(
            f"{BASE_URL}/predict-risk",
            json={
                "area": "Cantt",
                "crime_type": "Burglary",
                "date": "2025-10-15"
            }
        )
        
        assert response.status_code == 200, f"Existing endpoint broken: {response.text}"
        data = response.json()
        assert "risk_level" in data
        assert "risk_percentage" in data
        
        print("✅ Existing predict-risk endpoint still works")
    
    def test_existing_analyze_route_safety_still_works(self):
        """Test that existing analyze_route_safety endpoint still works"""
        response = requests.post(
            f"http://localhost:8000/analyze_route_safety",
            json={
                "start_lat": 31.5204,
                "start_lng": 74.3587,
                "end_lat": 31.5300,
                "end_lng": 74.3600
            }
        )
        
        # Should return 200 or 422 (validation error), but not 404
        assert response.status_code != 404, "Existing endpoint was removed"
        print("✅ Existing analyze_route_safety endpoint still works")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing AI Route Safety Analysis Implementation")
    print("="*60 + "\n")
    
    test = TestAIRouteSafetyAnalysis()
    
    try:
        test.test_ai_route_safety_endpoint_exists()
        test.test_ai_route_safety_response_structure()
        test.test_ai_route_safety_score_range()
        test.test_ai_route_safety_multiple_points()
        test.test_ai_route_safety_with_date()
        test.test_ai_route_safety_alerts_generated()
        test.test_existing_predict_risk_still_works()
        test.test_existing_analyze_route_safety_still_works()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

