# app/routes/analytics.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.core.database import get_db_connection
from app.dependencies import get_username_from_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])

@router.get("/crime-trends")
async def get_crime_trends(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    area: str = Query("all", description="Filter by area"),
    current_user: str = Depends(get_username_from_token)
):
    """
    Get crime trends with actual and predicted counts over time
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build query based on area filter
        if area == "all":
            query = """
                SELECT 
                    DATE(crime_date) as date,
                    COUNT(*) as actual_count
                FROM crimes
                WHERE crime_date BETWEEN %s AND %s
                GROUP BY DATE(crime_date)
                ORDER BY date
            """
            cursor.execute(query, (start_date, end_date))
        else:
            query = """
                SELECT 
                    DATE(crime_date) as date,
                    COUNT(*) as actual_count
                FROM crimes
                WHERE crime_date BETWEEN %s AND %s
                AND area = %s
                GROUP BY DATE(crime_date)
                ORDER BY date
            """
            cursor.execute(query, (start_date, end_date, area))
        
        results = cursor.fetchall()
        
        # Generate predictions (simple moving average for now)
        trends = []
        for i, row in enumerate(results):
            actual = row['actual_count']
            # Simple prediction: average of previous 3 days or current value
            if i >= 3:
                predicted = int((results[i-1]['actual_count'] + 
                               results[i-2]['actual_count'] + 
                               results[i-3]['actual_count']) / 3)
            else:
                predicted = actual
            
            trends.append({
                "date": row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else str(row['date']),
                "actual": actual,
                "predicted": predicted
            })
        
        cursor.close()
        conn.close()
        
        return {"trends": trends}
        
    except Exception as e:
        logger.error(f"Error fetching crime trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictive")
async def get_predictive_analytics(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: str = Depends(get_username_from_token)
):
    """
    Get predictive analytics including patterns and risk heatmaps
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get crime patterns by hour and day of week
        cursor.execute("""
            SELECT 
                HOUR(crime_date) as hour,
                DAYOFWEEK(crime_date) - 1 as day_of_week,
                COUNT(*) as count
            FROM crimes
            WHERE crime_date BETWEEN %s AND %s
            GROUP BY hour, day_of_week
        """, (start_date, end_date))
        
        pattern_data = cursor.fetchall()
        
        # Convert to patterns format
        patterns = []
        for row in pattern_data:
            patterns.append({
                "hour": row['hour'],
                "day_of_week": row['day_of_week'],
                "intensity": min(100, row['count'] * 5)  # Scale intensity
            })
        
        # Generate risk heatmap (7 days x 24 hours)
        heatmap = [[0 for _ in range(24)] for _ in range(7)]
        
        for row in pattern_data:
            day = row['day_of_week']
            hour = row['hour']
            count = row['count']
            heatmap[day][hour] = min(100, count * 10)  # Scale to 0-100
        
        cursor.close()
        conn.close()
        
        return {
            "patterns": patterns,
            "risk_heatmap": heatmap
        }
        
    except Exception as e:
        logger.error(f"Error fetching predictive analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/area-analysis")
async def get_area_analysis(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: str = Depends(get_username_from_token)
):
    """
    Get area-wise crime analysis
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get crime counts by area
        cursor.execute("""
            SELECT 
                area,
                COUNT(*) as crime_count,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk,
                SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk
            FROM crimes
            WHERE crime_date BETWEEN %s AND %s
            AND area IS NOT NULL
            GROUP BY area
            ORDER BY crime_count DESC
            LIMIT 20
        """, (start_date, end_date))
        
        area_data = cursor.fetchall()
        
        # Determine risk level for each area
        areas = []
        for row in area_data:
            crime_count = row['crime_count']
            high_risk = row['high_risk'] or 0
            medium_risk = row['medium_risk'] or 0
            
            # Calculate risk level
            if crime_count > 50 or high_risk > 20:
                risk_level = "High"
            elif crime_count > 20 or high_risk > 10:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            areas.append({
                "name": row['area'],
                "crime_count": crime_count,
                "risk_level": risk_level
            })
        
        cursor.close()
        conn.close()
        
        return {"areas": areas}
        
    except Exception as e:
        logger.error(f"Error fetching area analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
