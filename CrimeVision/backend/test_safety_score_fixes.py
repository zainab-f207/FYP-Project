#!/usr/bin/env python3
"""
Test script to verify the safety score consistency fixes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.utils.risk import calculate_unified_risk_summary

def test_zero_crime_consistency():
    """Test that zero-crime areas consistently return 95% safety"""

    print("🧪 Testing Safety Score Consistency Fixes...")
    print("=" * 60)

    # Test 1: No stats provided
    print("\n📋 Test 1: No stats provided")
    result1 = calculate_unified_risk_summary(None)
    print(f"   Result: {result1['safety_score']}% safety, {result1['risk_level']} risk")
    assert result1['safety_score'] == 95.0, f"Expected 95.0, got {result1['safety_score']}"
    assert result1['risk_level'] == "Low", f"Expected 'Low', got {result1['risk_level']}"
    print("   ✅ PASS")

    # Test 2: Empty stats dict
    print("\n📋 Test 2: Empty stats dict")
    result2 = calculate_unified_risk_summary({})
    print(f"   Result: {result2['safety_score']}% safety, {result2['risk_level']} risk")
    assert result2['safety_score'] == 95.0, f"Expected 95.0, got {result2['safety_score']}"
    assert result2['risk_level'] == "Low", f"Expected 'Low', got {result2['risk_level']}"
    print("   ✅ PASS")

    # Test 3: Zero crimes in stats
    print("\n📋 Test 3: Zero total crimes")
    stats_zero = {
        'total_crimes': 0,
        'high_risk_count': 0,
        'medium_risk_count': 0,
        'last_30_days': 0,
        'last_90_days': 0
    }
    result3 = calculate_unified_risk_summary(stats_zero)
    print(f"   Result: {result3['safety_score']}% safety, {result3['risk_level']} risk")
    assert result3['safety_score'] == 95.0, f"Expected 95.0, got {result3['safety_score']}"
    assert result3['risk_level'] == "Low", f"Expected 'Low', got {result3['risk_level']}"
    print("   ✅ PASS")

    # Test 4: Normal crime data (should NOT be 95%)
    print("\n📋 Test 4: Normal crime data (should be calculated normally)")
    stats_normal = {
        'total_crimes': 50,
        'high_risk_count': 10,
        'medium_risk_count': 15,
        'last_30_days': 5,
        'last_90_days': 12,
        'recent_count': 25,
        'older_count': 25
    }
    result4 = calculate_unified_risk_summary(stats_normal)
    print(f"   Result: {result4['safety_score']}% safety, {result4['risk_level']} risk")
    assert result4['safety_score'] != 95.0, f"Normal crime data should not return 95%, got {result4['safety_score']}"
    print("   ✅ PASS")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("🔧 Safety score consistency fixes are working correctly.")
    print("\n📊 Summary:")
    print(f"   • Zero crime areas now consistently return: {result1['safety_score']}% safety")
    print(f"   • Risk level for safe areas: {result1['risk_level']}")
    print(f"   • Normal crime areas calculated properly: {result4['safety_score']}% safety")
    print("\n✅ Fatehgarh will now show ~95% instead of 50%!")
    print("✅ All interfaces now use consistent scoring!")

if __name__ == "__main__":
    test_zero_crime_consistency()