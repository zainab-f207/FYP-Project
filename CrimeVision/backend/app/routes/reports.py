from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional, cast
import logging
from datetime import datetime, timedelta
import json

from app.core.database import get_db_connection
from app.dependencies import get_username_from_token
from app.reports import (
    generate_crime_summary_pdf,
    generate_crime_summary_excel,
    generate_crime_summary_csv,
    generate_user_activity_pdf,
    generate_user_activity_excel,
    generate_user_activity_csv,
    generate_system_health_pdf,
    generate_system_health_excel,
    generate_system_health_csv,
    get_crime_summary_data,
    get_system_health_data,
    get_user_activity_data,
    save_report_to_db,
    get_reports_from_db,
    get_scheduled_reports_from_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/crime-summary")
def get_crime_summary_report(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    area: Optional[str] = Query(None, description="Filter by area"),
    crime_type: Optional[str] = Query(None, description="Filter by crime type")
):
    """Generate crime summary report with statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        logger.info(f"User {current_user} requesting crime summary report")
        
        try:
            cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
            user_row = cursor.fetchone()
            if not user_row:
                logger.warning(f"User {current_user} not found in database")
                raise HTTPException(status_code=401, detail="User not found")
            user = cast(Dict[str, Any], user_row)
            user_role = user.get("role", "user")
            logger.info(f"User {current_user} has role: {user_role}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking user role for {current_user}: {e}")
            raise HTTPException(status_code=500, detail="Database error checking permissions")

        try:
            query = """
                SELECT
                    COUNT(*) as total_crimes,
                    COUNT(DISTINCT area) as unique_areas,
                    COUNT(DISTINCT crime_type) as unique_crime_types,
                    AVG(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) * 100 as high_risk_percentage,
                    AVG(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) * 100 as medium_risk_percentage,
                    AVG(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) * 100 as low_risk_percentage
                FROM crimes
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND crime_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND crime_date <= %s"
                params.append(end_date)
            if area:
                query += " AND area = %s"
                params.append(area)
            if crime_type:
                query += " AND crime_type = %s"
                params.append(crime_type)

            logger.info(f"Executing summary query with params: {params}")
            cursor.execute(query, params)
            summary_row = cursor.fetchone()
            summary = cast(Dict[str, Any], summary_row) if summary_row else {}
        except Exception as e:
            logger.error(f"Error executing summary query: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")

        try:
            area_query = """
                SELECT area, COUNT(*) as crime_count
                FROM crimes
                WHERE 1=1
            """
            area_params = []
            if start_date:
                area_query += " AND crime_date >= %s"
                area_params.append(start_date)
            if end_date:
                area_query += " AND crime_date <= %s"
                area_params.append(end_date)
            if crime_type:
                area_query += " AND crime_type = %s"
                area_params.append(crime_type)

            area_query += " GROUP BY area ORDER BY crime_count DESC LIMIT 10"
            cursor.execute(area_query, area_params)
            area_distribution = [cast(Dict[str, Any], row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error executing area distribution query: {e}")
            area_distribution = []

        try:
            type_query = """
                SELECT crime_type, COUNT(*) as crime_count
                FROM crimes
                WHERE 1=1
            """
            type_params = []
            if start_date:
                type_query += " AND crime_date >= %s"
                type_params.append(start_date)
            if end_date:
                type_query += " AND crime_date <= %s"
                type_params.append(end_date)
            if area:
                type_query += " AND area = %s"
                type_params.append(area)

            type_query += " GROUP BY crime_type ORDER BY crime_count DESC LIMIT 10"
            cursor.execute(type_query, type_params)
            type_distribution = [cast(Dict[str, Any], row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error executing type distribution query: {e}")
            type_distribution = []

        try:
            trend_query = """
                SELECT
                    DATE_FORMAT(crime_date, '%Y-%m') as month,
                    COUNT(*) as crime_count
                FROM crimes
                WHERE 1=1
            """
            trend_params = []
            if start_date:
                trend_query += " AND crime_date >= %s"
                trend_params.append(start_date)
            if end_date:
                trend_query += " AND crime_date <= %s"
                trend_params.append(end_date)
            if area:
                trend_query += " AND area = %s"
                trend_params.append(area)
            if crime_type:
                trend_query += " AND crime_type = %s"
                trend_params.append(crime_type)

            trend_query += " GROUP BY DATE_FORMAT(crime_date, '%Y-%m') ORDER BY month"
            cursor.execute(trend_query, trend_params)
            monthly_trend = [cast(Dict[str, Any], row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error executing monthly trend query: {e}")
            monthly_trend = []

        return {
            "summary": {
                "total_crimes": summary["total_crimes"],
                "unique_areas": summary["unique_areas"],
                "unique_crime_types": summary["unique_crime_types"],
                "high_risk_percentage": round(summary["high_risk_percentage"] or 0, 2),
                "medium_risk_percentage": round(summary["medium_risk_percentage"] or 0, 2),
                "low_risk_percentage": round(summary["low_risk_percentage"] or 0, 2)
            },
            "area_distribution": [
                {"area": row["area"], "count": row["crime_count"]}
                for row in area_distribution
            ],
            "crime_type_distribution": [
                {"crime_type": row["crime_type"], "count": row["crime_count"]}
                for row in type_distribution
            ],
            "monthly_trend": [
                {"month": row["month"], "count": row["crime_count"]}
                for row in monthly_trend
            ],
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "area": area,
                "crime_type": crime_type
            }
        }

    except Exception as e:
        logger.error(f"Database error generating crime summary report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/user-activity")
def get_user_activity_report(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_role: Optional[str] = Query(None, description="Filter by user role")
):
    """Generate user activity report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=403, detail="Access denied")
        user = cast(Dict[str, Any], user_row)
        if user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # User registration statistics
        reg_query = """
            SELECT
                COUNT(*) as total_users,
                COUNT(CASE WHEN role = 'user' THEN 1 END) as regular_users,
                COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
                COUNT(CASE WHEN role = 'superadmin' THEN 1 END) as superadmin_users,
                COUNT(CASE WHEN DATE(created_at) = CURDATE() THEN 1 END) as new_today,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 END) as new_this_week,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 1 END) as new_this_month
            FROM users_info
            WHERE 1=1
        """
        reg_params = []

        if user_role:
            reg_query += " AND role = %s"
            reg_params.append(user_role)

        cursor.execute(reg_query, reg_params)
        user_stats_row = cursor.fetchone()
        user_stats = cast(Dict[str, Any], user_stats_row) if user_stats_row else {}  # type: ignore[arg-type]

        # User activity logs summary
        activity_query = """
            SELECT
                activity_type,
                COUNT(*) as count
            FROM user_activity_logs
            WHERE 1=1
        """
        activity_params = []

        if start_date:
            activity_query += " AND DATE(created_at) >= %s"
            activity_params.append(start_date)
        if end_date:
            activity_query += " AND DATE(created_at) <= %s"
            activity_params.append(end_date)

        activity_query += " GROUP BY activity_type ORDER BY count DESC"
        cursor.execute(activity_query, activity_params)
        activity_summary = [cast(Dict[str, Any], row) for row in cursor.fetchall()]  # type: ignore[misc]

        # Recent user registrations
        recent_query = """
            SELECT username, first_name, last_name, email, role, created_at
            FROM users_info
            WHERE 1=1
        """
        recent_params = []

        if user_role:
            recent_query += " AND role = %s"
            recent_params.append(user_role)

        recent_query += " ORDER BY created_at DESC LIMIT 20"
        cursor.execute(recent_query, recent_params)
        recent_users = [cast(Dict[str, Any], row) for row in cursor.fetchall()]  # type: ignore[misc]

        return {
            "user_statistics": {
                "total_users": user_stats["total_users"],
                "regular_users": user_stats["regular_users"],
                "admin_users": user_stats["admin_users"],
                "superadmin_users": user_stats["superadmin_users"],
                "new_today": user_stats["new_today"],
                "new_this_week": user_stats["new_this_week"],
                "new_this_month": user_stats["new_this_month"]
            },
            "activity_summary": [
                {"activity_type": row["activity_type"], "count": row["count"]}
                for row in activity_summary
            ],
            "recent_registrations": [
                {
                    "username": row["username"],
                    "name": f"{row['first_name']} {row['last_name']}",
                    "email": row["email"],
                    "role": row["role"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in recent_users
            ],
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "user_role": user_role
            }
        }

    except Exception as e:
        logger.error(f"Database error generating user activity report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/system-health")
def get_system_health_report(current_user: str = Depends(get_username_from_token)):
    """Generate system health report"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=403, detail="Access denied")
        user = cast(Dict[str, Any], user_row)
        if user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Database connection health
        db_health = "healthy"
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        except Exception as e:
            db_health = f"unhealthy: {str(e)}"

        # Table statistics
        tables_stats = {}
        tables = ["users_info", "crimes", "admins", "user_activity_logs", "audit_logs"]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result_row = cursor.fetchone()
                if result_row:
                    result = cast(Dict[str, Any], result_row)  # type: ignore[arg-type]
                    tables_stats[table] = result.get("count", 0)
                else:
                    tables_stats[table] = 0
            except Exception as e:
                tables_stats[table] = f"error: {str(e)}"

        # System metrics
        cursor.execute("SELECT COUNT(*) as active_users FROM users_info WHERE role = 'user'")
        active_users_row = cursor.fetchone()
        active_users = cast(Dict[str, Any], active_users_row).get("active_users", 0) if active_users_row else 0  # type: ignore[arg-type]

        cursor.execute("SELECT COUNT(*) as total_crimes FROM crimes")
        total_crimes_row = cursor.fetchone()
        total_crimes = cast(Dict[str, Any], total_crimes_row).get("total_crimes", 0) if total_crimes_row else 0  # type: ignore[arg-type]

        cursor.execute("SELECT COUNT(*) as recent_activities FROM user_activity_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        recent_activities_row = cursor.fetchone()
        recent_activities = cast(Dict[str, Any], recent_activities_row).get("recent_activities", 0) if recent_activities_row else 0  # type: ignore[arg-type]

        # ML model status (would need to import from main app if needed)
        ml_status = "not_available"

        return {
            "database_health": db_health,
            "table_statistics": tables_stats,
            "system_metrics": {
                "active_users": active_users,
                "total_crimes": total_crimes,
                "recent_activities_24h": recent_activities,
                "ml_model_status": ml_status
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Database error generating system health report: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()

@router.get("/export-crime-data")
def export_crime_data(
    current_user: str = Depends(get_username_from_token),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    area: Optional[str] = Query(None, description="Filter by area"),
    crime_type: Optional[str] = Query(None, description="Filter by crime type"),
    format: str = Query("json", description="Export format: json or csv")
):
    """Export crime data for reporting purposes"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user has admin privileges
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(status_code=403, detail="Access denied")
        user = cast(Dict[str, Any], user_row)
        if user.get("role") not in ["superadmin", "admin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Build query
        query = """
            SELECT
                id, area, crime_type, crime_date, latitude, longitude, risk_level, created_at
            FROM crimes
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND crime_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND crime_date <= %s"
            params.append(end_date)
        if area:
            query += " AND area = %s"
            params.append(area)
        if crime_type:
            query += " AND crime_type = %s"
            params.append(crime_type)

        query += " ORDER BY crime_date DESC"

        cursor.execute(query, params)
        crimes = [cast(Dict[str, Any], row) for row in cursor.fetchall()]  # type: ignore[misc]

        # Format data
        export_data = []
        for crime in crimes:
            export_data.append({
                "id": crime["id"],
                "area": crime["area"],
                "crime_type": crime["crime_type"],
                "crime_date": str(crime["crime_date"]),
                "latitude": crime["latitude"],
                "longitude": crime["longitude"],
                "risk_level": crime["risk_level"],
                "created_at": crime["created_at"].isoformat() if crime["created_at"] else None
            })

        if format.lower() == "csv":
            # Convert to CSV format
            if not export_data:
                csv_content = "No data available"
            else:
                headers = list(export_data[0].keys())
                csv_content = ",".join(headers) + "\n"
                for row in export_data:
                    csv_row = ",".join(str(row.get(header, "")) for header in headers)
                    csv_content += csv_row + "\n"

            return {
                "format": "csv",
                "data": csv_content,
                "record_count": len(export_data),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "area": area,
                    "crime_type": crime_type
                }
            }
        else:
            # Default JSON format
            return {
                "format": "json",
                "data": export_data,
                "record_count": len(export_data),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "area": area,
                    "crime_type": crime_type
                }
            }

    except Exception as e:
        logger.error(f"Database error exporting crime data: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        cursor.close()
        conn.close()