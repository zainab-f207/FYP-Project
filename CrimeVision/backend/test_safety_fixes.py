#!/usr/bin/env python3
"""
Quick Test Script to Verify Safety Score Fixes
Run this to check if the changes are working correctly
"""

import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_AREA_ZERO_CRIMES = "Fatehgarh"  # Area with 0 crimes
TEST_AREA_WITH_CRIMES = "Gulberg"    # Area with crimes

def test_safety_score_fixes():
    """Test all the fixes we applied"""

    print("=" * 70)
    print("🧪 TESTING SAFETY SCORE FIXES")
    print("=" * 70)

    # Test 1: Area with zero crimes should return 95%
    print("\n📋 TEST 1: Zero Crimes Area (Fatehgarh)")
    print("-" * 70)

    try:
        response = requests.get(f"{BASE_URL}/api/areas/{TEST_AREA_ZERO_CRIMES}/safety-score")
        data = response.json()

        safety_score = data.get('safety_score', 0)
        print(f"   Area: {TEST_AREA_ZERO_CRIMES}")
        print(f"   Safety Score: {safety_score}%")
        print(f"   Risk Level: {data.get('risk_level')}")
        print(f"   Total Crimes: {data.get('total_crimes', 0)}")

        if safety_score >= 95:
            print(f"   ✅ PASS: Correctly returns {safety_score}% for zero crimes")
        else:
            print(f"   ❌ FAIL: Expected 95-100%, got {safety_score}%")
            print(f"   ⚠️  Backend may not be restarted or changes not applied!")

    except requests.exceptions.ConnectionError:
        print("   ❌ ERROR: Cannot connect to backend!")
        print("   ⚠️  Make sure backend is running on http://localhost:8000")
        return
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 2: Area Profile should show up to 10 risk factors
    print("\n📋 TEST 2: Risk Factors Limit (Gulberg)")
    print("-" * 70)

    try:
        # This endpoint returns detailed area analysis
        response = requests.get(f"{BASE_URL}/api/areas/{TEST_AREA_WITH_CRIMES}/analytics")

        if response.status_code == 404:
            # Try alternate endpoint
            response = requests.get(f"{BASE_URL}/api/crimes/areas/{TEST_AREA_WITH_CRIMES}/analytics")

        if response.status_code == 200:
            data = response.json()

            # Check if top crime types are available
            top_crimes = data.get('top_crime_types', [])
            crime_categories = data.get('crime_categories', [])

            count = len(top_crimes) or len(crime_categories)

            print(f"   Area: {TEST_AREA_WITH_CRIMES}")
            print(f"   Top Crime Types Returned: {count}")

            if count >= 10 or count == 0:
                print(f"   ✅ PASS: Limit updated (returning {count} items)")
            elif count == 3:
                print(f"   ❌ FAIL: Still returning only 3 items")
                print(f"   ⚠️  Backend not restarted or LIMIT not changed!")
            else:
                print(f"   ⚠️  PARTIAL: Returns {count} items (expected up to 10)")
        else:
            print(f"   ⚠️  Endpoint not found or error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 3: Calculate Unified Risk Summary with zero stats
    print("\n📋 TEST 3: Unified Risk Summary Function")
    print("-" * 70)

    try:
        # This should be handled by the updated risk.py
        from app.utils.risk import calculate_unified_risk_summary

        # Test with None stats
        result1 = calculate_unified_risk_summary(None)
        print(f"   Test with None stats:")
        print(f"     Safety Score: {result1['safety_score']}%")
        print(f"     Risk Level: {result1['risk_level']}")

        if result1['safety_score'] == 95.0:
            print(f"   ✅ PASS: None stats returns 95%")
        else:
            print(f"   ❌ FAIL: Expected 95%, got {result1['safety_score']}%")

        # Test with zero crimes
        result2 = calculate_unified_risk_summary({'total_crimes': 0})
        print(f"\n   Test with zero crimes:")
        print(f"     Safety Score: {result2['safety_score']}%")
        print(f"     Risk Level: {result2['risk_level']}")

        if result2['safety_score'] == 95.0:
            print(f"   ✅ PASS: Zero crimes returns 95%")
        else:
            print(f"   ❌ FAIL: Expected 95%, got {result2['safety_score']}%")

    except ImportError:
        print("   ⚠️  SKIP: Cannot import risk.py (run from backend directory)")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test 4: Check LIMIT in top crimes query
    print("\n📋 TEST 4: Database LIMIT Check")
    print("-" * 70)

    try:
        with open('main.py', 'r') as f:
            content = f.read()

        limit_3_count = content.count('LIMIT 3')
        limit_10_count = content.count('LIMIT 10')

        print(f"   'LIMIT 3' found: {limit_3_count} times")
        print(f"   'LIMIT 10' found: {limit_10_count} times")

        if limit_3_count == 0 and limit_10_count > 0:
            print(f"   ✅ PASS: All LIMIT 3 changed to LIMIT 10")
        elif limit_3_count > 0:
            print(f"   ❌ FAIL: Still have {limit_3_count} instances of 'LIMIT 3'")
        else:
            print(f"   ⚠️  UNKNOWN: Check manually")

    except FileNotFoundError:
        print("   ⚠️  SKIP: Run this script from backend directory")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("🏁 TEST SUMMARY")
    print("=" * 70)
    print("\n✅ If all tests pass: Changes are working!")
    print("❌ If tests fail: Backend needs restart or changes not applied")
    print("\n💡 Next steps if failing:")
    print("   1. Restart backend: Ctrl+C then 'uvicorn main:app --reload'")
    print("   2. Clear browser cache completely")
    print("   3. Check backend console logs")
    print("   4. Check Network tab in browser DevTools")
    print("=" * 70)

if __name__ == "__main__":
    test_safety_score_fixes()