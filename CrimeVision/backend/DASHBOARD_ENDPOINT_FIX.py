"""
FIXED /api/auth/me/stats ENDPOINT FOR main_enhanced_final_fixed.py

Replace the entire function body (lines 5298-5355) with this implementation:
"""

    """Get user statistics for dashboard with crime data and safety scores"""
    conn = None
    cursor = None
    try:
        # Determine time delta based on filter
        logger.info(f"📊 Stats requested: lat={latitude}, lon={longitude}, area='{area}', filter={time_filter}")

        if time_filter == '7d':
            days_delta = 7
        elif time_filter == '30d':
            days_delta = 30
        elif time_filter == '12m' or time_filter == '1y':
            days_delta = 365
        elif time_filter == 'all':
            days_delta = None  # No time restriction - get ALL historical data
        else:
            days_delta = 365

        # Build date filter SQL fragment - only add if days_delta is specified
        if days_delta:
            date_filter_sql = f"AND crime_date >= DATE_SUB(NOW(), INTERVAL {days_delta} DAY)"
        else:
            date_filter_sql = ""  # No date restriction for "All Time"

        logger.info(f"📊 Dashboard stats: time_filter={time_filter}, days_delta={days_delta}, area={area}, lat={latitude}, lng={longitude}")
        logger.info(f"📊 Date filter SQL: {date_filter_sql}")

        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("Database connection not available")

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, home_area, home_latitude, home_longitude FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()

        if not user:
            return {
                "safety_score": 0,
                "weekly_alerts": 0,
                "safe_routes": 0,
                "nearest_safe_zone": 0,
                "safe_zone_name": "N/A",
                "time_filter": time_filter
            }

        user = cast(Dict[str, Any], user)
        user_id = user['id']
        home_area = user['home_area']

        lat = latitude if latitude is not None else user['home_latitude']
        lon = longitude if longitude is not None else user['home_longitude']

        safety_score = 0.0
        safety_score_change = 0.0
        resolved_area = home_area or "Unknown"
        confidence = "very_high"

        crime_counts = []
        day_crimes = 0
        night_crimes = 0
        weekly_alerts = 0
        weekly_alerts_change = 0
        recent_7d_crimes = 0
        recent_30d_crimes = 0
        previous_7d_crimes = 0
        safe_routes = 0
        nearest_safe_zone = 0
        safe_zone_name = "N/A"
        current_stats = None
        trend_data = []
        trend_labels = []
        sub_areas = []
        total_crimes = 0
        high_risk_crimes = 0
        medium_risk_crimes = 0
        unique_crime_types = 0
        top_crimes_list = []
        system_status = []

        # 1. Query crimes based on available data
        explicit_area = area
        scope_radius_meters = 1500

        # Step A: Direct area name match (highest confidence)
        if explicit_area:
            search_pattern = f"%{explicit_area}%"
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes
                WHERE area LIKE %s
                {date_filter_sql}
            """, (search_pattern,))
            current_stats = cursor.fetchone()
            confidence = "medium"
            resolved_area = explicit_area

        # Step B: Fallback to Radius (1.5km) only when no explicit area is provided or no data found
        if not explicit_area and (not current_stats or current_stats.get("total_crimes", 0) == 0) and lat and lon:
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes
                WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters}
                {date_filter_sql}
            """, (lon, lat))
            current_stats = cursor.fetchone()
            confidence = "high"

        # Step C: Final fallback to home area
        if not explicit_area and (not current_stats or current_stats.get("total_crimes", 0) == 0) and home_area:
            search_pattern = f"%{home_area}%"
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_crimes,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count,
                    SUM(CASE WHEN risk_level IS NULL OR risk_level = 'Unknown' THEN 1 ELSE 0 END) as unknown_risk_count,
                    COUNT(DISTINCT crime_type) as unique_crime_types
                FROM crimes
                WHERE area LIKE %s
                {date_filter_sql}
            """, (search_pattern,))
            current_stats = cursor.fetchone()
            confidence = "low"
            resolved_area = home_area

        # 2. Calculate safety scores if we found data
        zero_incident_period = current_stats is not None and current_stats.get("total_crimes", 0) == 0
        logger.info(f"🔍 Safety calculation: current_stats={current_stats is not None}, total_crimes={current_stats.get('total_crimes', 0) if current_stats else 'N/A'}, zero_incident_period={zero_incident_period}")

        if current_stats and current_stats.get("total_crimes", 0) > 0:
            from app.utils.risk import calculate_safety_score
            safety_score = float(calculate_safety_score(current_stats, days_delta))

            # Get crime breakdown and timing patterns
            if (confidence == "medium" or confidence == "low") and resolved_area:
                search_pattern = f"%{resolved_area}%"
                cursor.execute(f"SELECT crime_type, COUNT(*) as count FROM crimes WHERE area LIKE %s {date_filter_sql} GROUP BY crime_type", (search_pattern,))
                crime_counts = cursor.fetchall()
                cursor.execute(f"SELECT SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes, SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes FROM crimes WHERE area LIKE %s {date_filter_sql}", (search_pattern,))
                time_stats = cursor.fetchone()
            else: # Radius breakdown
                cursor.execute(f"SELECT crime_type, COUNT(*) as count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} {date_filter_sql} GROUP BY crime_type", (lon, lat))
                crime_counts = cursor.fetchall()
                cursor.execute(f"SELECT SUM(CASE WHEN HOUR(crime_date) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes, SUM(CASE WHEN HOUR(crime_date) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= {scope_radius_meters} {date_filter_sql}", (lon, lat))
                time_stats = cursor.fetchone()

        elif zero_incident_period:
            # Area found but ZERO incidents in selected window — this is VERY SAFE
            safety_score = 95.0
            logger.info(f"✅ Zero incident period detected for {resolved_area} (time_filter={time_filter}) → safety_score set to 95.0")
            safety_score_change = 0.0
            crime_counts = []

        # Extract values from time_stats
        if time_stats:
            day_crimes = int(time_stats.get('day_crimes', 0))
            night_crimes = int(time_stats.get('night_crimes', 0))

        from app.utils.risk import calculate_breakdown
        breakdown = calculate_breakdown(crime_counts or [], day_crimes, night_crimes)

        # 3. Get alert counts and changes
        if (confidence == "medium" or confidence == "low") and resolved_area:
            search_pattern = f"%{resolved_area}%"
            cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s {date_filter_sql}", (search_pattern,))
            weekly_alerts = cursor.fetchone()['count']

            # Previous period comparison - only if days_delta is specified
            if days_delta:
                cursor.execute(f"SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL {2*days_delta} DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL {days_delta} DAY)", (search_pattern,))
                prev_alerts = cursor.fetchone()['count']
                weekly_alerts_change = weekly_alerts - prev_alerts
            else:
                weekly_alerts_change = 0

            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            recent_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 14 DAY) AND crime_date < DATE_SUB(NOW(), INTERVAL 7 DAY)", (search_pattern,))
            previous_7d_crimes = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s AND crime_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (search_pattern,))
            recent_30d_crimes = cursor.fetchone()['count']

            cursor.execute(f"""
                SELECT crime_type, COUNT(*) as count
                FROM crimes
                WHERE area LIKE %s {date_filter_sql}
                GROUP BY crime_type
                ORDER BY count DESC
                LIMIT 10
            """, (search_pattern,))
            top_rows = cursor.fetchall() or []

        # Build top crimes list for response
        top_crimes_list = []
        for row in (top_rows if 'top_rows' in locals() else []):
            top_crimes_list.append({
                "crime_type": row.get('crime_type', 'Unknown'),
                "count": int(row.get('count', 0))
            })

        # Extract summary values
        total_crimes = int((current_stats.get("total_crimes") or 0)) if current_stats else 0
        high_risk_crimes = int((current_stats.get("high_risk_count") or 0)) if current_stats else 0
        medium_risk_crimes = int((current_stats.get("medium_risk_count") or 0)) if current_stats else 0
        unique_crime_types = int((current_stats.get("unique_crime_types") or 0)) if current_stats else 0

        from app.utils.risk import get_risk_level
        risk_level = get_risk_level(safety_score)

        logger.info(f"📤 FINAL RESPONSE: safety_score={safety_score}, risk_level={risk_level}, total_crimes={total_crimes}, area={resolved_area}, time_filter={time_filter}")

        return {
            "safety_score": safety_score,
            "risk_score": round(100.0 - safety_score, 1),
            "safety_score_change": safety_score_change,
            "risk_level": risk_level,
            "weekly_alerts": weekly_alerts,
            "weekly_alerts_change": weekly_alerts_change,
            "recent_7d_crimes": recent_7d_crimes,
            "recent_30d_crimes": recent_30d_crimes,
            "previous_7d_crimes": previous_7d_crimes,
            "safe_routes": safe_routes,
            "nearest_safe_zone": nearest_safe_zone,
            "safe_zone_name": safe_zone_name,
            "breakdown": breakdown,
            "total_crimes": total_crimes,
            "high_risk_crimes": high_risk_crimes,
            "medium_risk_crimes": medium_risk_crimes,
            "unique_crime_types": unique_crime_types,
            "top_crimes_list": top_crimes_list,
            "resolved_area": resolved_area,
            "confidence": confidence,
            "data_confidence": "medium" if total_crimes > 10 else "low",
            "score_components": {},
            "trend_data": trend_data,
            "trend_labels": trend_labels,
            "sub_areas": sub_areas,
            "system_status": system_status,
            "time_filter": time_filter
        }
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        return {
            "safety_score": 50.0,
            "risk_score": 50.0,
            "safety_score_change": 0.0,
            "risk_level": "Moderate",
            "weekly_alerts": 0,
            "weekly_alerts_change": 0,
            "recent_7d_crimes": 0,
            "recent_30d_crimes": 0,
            "previous_7d_crimes": 0,
            "safe_routes": 0,
            "nearest_safe_zone": 0,
            "safe_zone_name": "N/A",
            "breakdown": {"violent": 0, "property": 0, "personal": 0, "day": 0, "night": 0},
            "total_crimes": 0,
            "high_risk_crimes": 0,
            "top_crimes_list": [],
            "resolved_area": "Unknown",
            "confidence": "none",
            "data_confidence": "none",
            "trend_data": [],
            "trend_labels": [],
            "time_filter": time_filter
        }
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()