#!/usr/bin/env python3
"""
Debug "All Time" Dashboard Functionality
"""
import os
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def test_all_time_queries():
    """Test the All Time queries directly"""
    print("=" * 60)
    print("DEBUGGING 'ALL TIME' DASHBOARD FUNCTIONALITY")
    print("=" * 60)

    try:
        # Database connection
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'crimevision_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor(dictionary=True)

        # Test area matching for Gulberg
        print("\n1. TESTING GULBERG AREA MATCHING")
        search_patterns = ['%gulberg%', '%Gulberg%', '%GULBERG%']

        for pattern in search_patterns:
            cursor.execute("SELECT COUNT(*) as total FROM crimes WHERE area LIKE %s", (pattern,))
            result = cursor.fetchone()
            print(f"Pattern '{pattern}': {result['total']} total incidents")

        # Test time filter logic
        print("\n2. TESTING TIME FILTER LOGIC")

        # Simulate "All Time" (days_delta = None)
        days_delta = None
        if days_delta:
            date_filter_sql = f"AND crime_date >= DATE_SUB(NOW(), INTERVAL {days_delta} DAY)"
        else:
            date_filter_sql = ""  # No date restriction for "All Time"

        print(f"Days delta: {days_delta}")
        print(f"Date filter SQL: '{date_filter_sql}'")

        # Test main query for Gulberg with "All Time"
        print("\n3. TESTING MAIN QUERY FOR GULBERG")
        search_pattern = '%gulberg%'
        main_query = f"""
            SELECT
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                COUNT(DISTINCT crime_type) as unique_crime_types
            FROM crimes
            WHERE area LIKE %s
            {date_filter_sql}
        """

        print(f"Query: {main_query}")
        cursor.execute(main_query, (search_pattern,))
        result = cursor.fetchone()
        print(f"Result: {result}")

        # Test different time filters for comparison
        print("\n4. TESTING DIFFERENT TIME FILTERS")
        time_filters = {
            '7d': 7,
            '30d': 30,
            '12m': 365,
            'all': None
        }

        for filter_name, days in time_filters.items():
            if days:
                filter_sql = f"AND crime_date >= DATE_SUB(NOW(), INTERVAL {days} DAY)"
            else:
                filter_sql = ""

            query = f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s {filter_sql}"
            cursor.execute(query, (search_pattern,))
            result = cursor.fetchone()
            print(f"{filter_name:>4}: {result['count']:>6} incidents")

        # Test what areas actually exist
        print("\n5. TESTING ACTUAL AREA NAMES")
        cursor.execute("SELECT DISTINCT area FROM crimes WHERE area LIKE %s LIMIT 10", (search_pattern,))
        areas = cursor.fetchall()
        print("Matching area names:")
        for area in areas:
            print(f"  - {area['area']}")

        # Test recent incidents vs all time
        print("\n6. TESTING RECENT VS ALL TIME")
        cursor.execute("SELECT MIN(crime_date) as oldest, MAX(crime_date) as newest, COUNT(*) as total FROM crimes WHERE area LIKE %s", (search_pattern,))
        result = cursor.fetchone()
        print(f"Date range: {result['oldest']} to {result['newest']}")
        print(f"Total incidents: {result['total']}")

        print("\n" + "=" * 60)
        print("DEBUG SUMMARY")
        print("=" * 60)
        print("If 'All Time' shows 0 incidents but total > 0, then:")
        print("1. Check if backend server was restarted")
        print("2. Check if frontend is sending time_filter=all")
        print("3. Check for caching issues")

    except Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    test_all_time_queries()