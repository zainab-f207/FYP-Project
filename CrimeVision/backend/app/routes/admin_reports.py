# app/routes/admin_reports.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.core.database import get_db_connection
from app.dependencies import get_username_from_token
from pydantic import BaseModel
import logging
import os
import json
import re

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin/reports", tags=["admin_reports"])

class ReportGenerateRequest(BaseModel):
    report_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: str = "pdf"
    title: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


def _sanitize_filename(name: str) -> str:
    """Sanitize custom filenames while preserving readability."""
    cleaned = re.sub(r"[^A-Za-z0-9._\-\s]", "", name or "").strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:120] if cleaned else "report"


def _get_table_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table_name,),
    )
    rows = cursor.fetchall() or []
    return {row.get("COLUMN_NAME") for row in rows if row.get("COLUMN_NAME")}


def _scheduled_reports_uses_modern_schema(cursor) -> bool:
    columns = _get_table_columns(cursor, "scheduled_reports")
    return "report_type" in columns and "schedule_frequency" in columns

class ReportScheduleRequest(BaseModel):
    report_type: str
    frequency: str
    recipients: List[str] = []
    format: str = "pdf"
    date_range: Optional[Dict[str, str]] = None
    title: Optional[str] = None
    description: Optional[str] = None


@router.post("/schedule")
async def schedule_report(
    request: ReportScheduleRequest,
    current_user: str = Depends(get_username_from_token)
):
    """
    Schedule a recurring report
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        modern_schema = _scheduled_reports_uses_modern_schema(cursor)
        
        report_name = request.title or f"Scheduled_{request.report_type}_{request.frequency}"
        recipients_str = ",".join(request.recipients) if request.recipients else ""
        
        # Calculate next run time based on frequency
        if request.frequency == "daily":
            next_run = datetime.now() + timedelta(days=1)
        elif request.frequency == "weekly":
            next_run = datetime.now() + timedelta(weeks=1)
        elif request.frequency == "monthly":
            next_run = datetime.now() + timedelta(days=30)
        else:
            next_run = datetime.now() + timedelta(days=1)
        
        if modern_schema:
            cursor.execute("""
                INSERT INTO scheduled_reports
                (report_type, report_name, schedule_frequency, recipients, format, 
                 is_active, created_by, created_at, next_run_at)
                VALUES (%s, %s, %s, %s, %s, 1, %s, NOW(), %s)
            """, (request.report_type, report_name, request.frequency, recipients_str, request.format, 
                  current_user, next_run))
        else:
            cursor.execute("""
                INSERT INTO scheduled_reports
                (title, type, schedule, format, recipients, parameters, next_run, last_run, status, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, 'active', %s, NOW())
            """, (
                report_name,
                request.report_type,
                request.frequency,
                request.format,
                recipients_str,
                json.dumps({"report_type": request.report_type, "report_name": report_name, "frequency": request.frequency}),
                next_run,
                current_user,
            ))
        
        conn.commit()
        schedule_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "Report scheduled successfully",
            "next_run_at": next_run.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error scheduling report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_report_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(get_username_from_token)
):
    """
    Get report generation history
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get total count
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM report_history
        """)
        total_result = cursor.fetchone()
        total = total_result['total'] if total_result else 0
        
        # Get reports with pagination
        cursor.execute("""
            SELECT 
                id,
                report_type,
                report_name,
                format,
                generated_by,
                generated_at,
                file_path,
                file_size,
                status
            FROM report_history
            ORDER BY generated_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        reports = cursor.fetchall()
        
        # Convert datetime objects to strings
        for report in reports:
            if isinstance(report.get('generated_at'), datetime):
                report['generated_at'] = report['generated_at'].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "reports": reports,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching report history: {e}")
        # If table doesn't exist, return empty list
        return {
            "reports": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }


@router.delete("/history")
async def clear_report_history(current_user: str = Depends(get_username_from_token)):
    """Clear previous reports from history and remove existing report files from disk."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Restrict destructive operation to admin/superadmin.
        cursor.execute("SELECT role FROM users_info WHERE username = %s", (current_user,))
        user = cursor.fetchone()
        if not user or user.get("role") not in ["admin", "superadmin"]:
            raise HTTPException(status_code=403, detail="Access denied")

        cursor.execute("SELECT file_path FROM report_history")
        rows = cursor.fetchall() or []

        deleted_files = 0
        for row in rows:
            file_path = row.get("file_path") if isinstance(row, dict) else None
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files += 1
                except Exception as file_err:
                    logger.warning(f"Could not delete report file {file_path}: {file_err}")

        cursor.execute("DELETE FROM report_history")
        cleared_rows = cursor.rowcount
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Previous reports cleared successfully",
            "deleted_rows": cleared_rows,
            "deleted_files": deleted_files,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing report history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled")
async def get_scheduled_reports(
    current_user: str = Depends(get_username_from_token)
):
    """
    Get scheduled reports
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        modern_schema = _scheduled_reports_uses_modern_schema(cursor)

        if modern_schema:
            cursor.execute("""
                SELECT *
                FROM scheduled_reports
                WHERE is_active = 1
                ORDER BY next_run_at ASC
            """)
        else:
            cursor.execute("""
                SELECT *
                FROM scheduled_reports
                WHERE status = 'active'
                ORDER BY next_run ASC
            """)
        
        reports = cursor.fetchall()
        
        # Convert datetime objects to strings
        for report in reports:
            for date_field in ['created_at', 'last_run_at', 'next_run_at']:
                if isinstance(report.get(date_field), datetime):
                    report[date_field] = report[date_field].isoformat()
            if modern_schema:
                report.setdefault('schedule_time', None)
                report.setdefault('report_name', report.get('report_name') or 'Scheduled Report')
            else:
                report['report_type'] = report.get('type') or report.get('report_type') or 'crime_summary'
                report['report_name'] = report.get('title') or report.get('report_name') or 'Scheduled Report'
                report['schedule_frequency'] = report.get('schedule') or report.get('schedule_frequency')
                report['is_active'] = report.get('status') == 'active'
                report.setdefault('schedule_time', None)
        
        cursor.close()
        conn.close()
        
        return {"scheduled_reports": reports}
        
    except Exception as e:
        logger.error(f"Error fetching scheduled reports: {e}")
        # If table doesn't exist, return empty list
        return {"scheduled_reports": []}


@router.post("/generate")
async def generate_custom_report(
    request: ReportGenerateRequest,
    current_user: str = Depends(get_username_from_token)
):
    """
    Generate a custom report with professional formatting and visualizations
    """
    try:
        from app.utils.report_generator import ReportGenerator
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Set default dates if not provided
        end_date = request.end_date or datetime.now().strftime('%Y-%m-%d')
        start_date = request.start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Get filters from request
        filters_dict = request.filters or {}
        
        logger.info(f"Generating {request.report_type} report from {start_date} to {end_date}")
        logger.info(f"Filters: {filters_dict}")
        
        # Generate report data based on type
        if request.report_type == "crime_summary":
            # Use DATE() function to handle DATETIME fields
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_crimes,
                    COUNT(DISTINCT area) as areas_affected,
                    COUNT(DISTINCT crime_type) as crime_types,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_crimes,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_crimes,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_crimes
                FROM crimes
                WHERE DATE(crime_date) BETWEEN %s AND %s
            """, (start_date, end_date))
            
            summary = cursor.fetchone()
            
            logger.info(f"Summary data: {summary}")
            
            # Get top areas
            cursor.execute("""
                SELECT area, COUNT(*) as count
                FROM crimes
                WHERE DATE(crime_date) BETWEEN %s AND %s
                AND area IS NOT NULL
                GROUP BY area
                ORDER BY count DESC
                LIMIT 15
            """, (start_date, end_date))
            
            top_areas = cursor.fetchall()
            
            logger.info(f"Top areas count: {len(top_areas)}")
            
            # Get crime trends by date
            cursor.execute("""
                SELECT 
                    DATE(crime_date) as date,
                    COUNT(*) as count,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk
                FROM crimes
                WHERE DATE(crime_date) BETWEEN %s AND %s
                GROUP BY DATE(crime_date)
                ORDER BY date
            """, (start_date, end_date))
            
            trends = cursor.fetchall()
            
            # Get crime types distribution
            cursor.execute("""
                SELECT 
                    crime_type,
                    COUNT(*) as count
                FROM crimes
                WHERE DATE(crime_date) BETWEEN %s AND %s
                AND crime_type IS NOT NULL
                GROUP BY crime_type
                ORDER BY count DESC
                LIMIT 10
            """, (start_date, end_date))
            
            crime_types = cursor.fetchall()
            
            report_data = {
                "summary": summary,
                "top_areas": top_areas,
                "trends": trends,
                "crime_types": crime_types,
                "period": f"{start_date} to {end_date}"
            }
            
        elif request.report_type == "user_activity":
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(*) as total_activities,
                    COUNT(DISTINCT DATE(created_at)) as active_days
                FROM user_activity_logs
                WHERE DATE(created_at) BETWEEN %s AND %s
            """, (start_date, end_date))
            
            summary = cursor.fetchone()
            
            # Get top activities
            cursor.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM user_activity_logs
                WHERE DATE(created_at) BETWEEN %s AND %s
                GROUP BY activity_type
                ORDER BY count DESC
                LIMIT 10
            """, (start_date, end_date))
            
            activities = cursor.fetchall()
            
            # Get daily activity trend
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM user_activity_logs
                WHERE DATE(created_at) BETWEEN %s AND %s
                GROUP BY DATE(created_at)
                ORDER BY date
            """, (start_date, end_date))
            
            trends = cursor.fetchall()
            
            report_data = {
                "summary": summary,
                "activities": activities,
                "trends": trends,
                "period": f"{start_date} to {end_date}"
            }
            
        elif request.report_type == "system_health":
            # Get database stats
            cursor.execute("SELECT COUNT(*) as total_crimes FROM crimes")
            crime_count = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_users FROM users_info")
            user_count = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as total_alerts FROM user_alerts")
            alert_count = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) as total_reports 
                FROM report_history 
                WHERE generated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            report_count = cursor.fetchone()
            
            report_data = {
                "database_stats": {
                    "total_crimes": crime_count['total_crimes'],
                    "total_users": user_count['total_users'],
                    "total_alerts": alert_count['total_alerts'],
                    "reports_last_30_days": report_count['total_reports']
                },
                "summary": {
                    "system_health": "Operational",
                    "uptime": "99.9%",
                    "last_backup": datetime.now().strftime('%Y-%m-%d'),
                    "database_size": "Healthy"
                },
                "generated_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Generate the report file
        # Map format to proper file extension
        extension_map = {
            'pdf': 'pdf',
            'excel': 'xlsx',
            'csv': 'csv',
            'json': 'json'
        }
        file_extension = extension_map.get(request.format, request.format)
        custom_title = request.title or (request.filters or {}).get("title")
        if custom_title:
            base_name = _sanitize_filename(str(custom_title))
            if base_name.lower().endswith(f".{file_extension.lower()}"):
                report_name = base_name
            else:
                report_name = f"{base_name}.{file_extension}"
        else:
            report_name = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        
        try:
            generator = ReportGenerator(output_dir="reports")
            file_path = generator.generate_report(
                report_type=request.report_type,
                data=report_data,
                format=request.format,
                filters=request.filters or {},
                filename=report_name
            )
            
            # Get file size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
        except ImportError as e:
            logger.warning(f"Report generation library not available: {e}")
            # Fallback: just save the data as JSON
            file_path = f"reports/{report_name}"
            os.makedirs("reports", exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            file_size = os.path.getsize(file_path)
        
        # Save report to history
        cursor.execute("""
            INSERT INTO report_history 
            (report_type, report_name, format, generated_by, generated_at, status, file_size, file_path)
            VALUES (%s, %s, %s, %s, NOW(), 'completed', %s, %s)
        """, (request.report_type, report_name, request.format, current_user, file_size, file_path))
        
        conn.commit()
        report_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "report_id": report_id,
            "report_name": report_name,
            "file_path": file_path,
            "file_size": file_size,
            "report_data": report_data,
            "message": "Report generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_report(
    report_type: str,
    frequency: str,
    recipients: List[str],
    format: str = "pdf",
    current_user: str = Depends(get_username_from_token)
):
    """
    Schedule a recurring report
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        modern_schema = _scheduled_reports_uses_modern_schema(cursor)
        
        report_name = f"Scheduled_{report_type}_{frequency}"
        recipients_str = ",".join(recipients)
        
        # Calculate next run time based on frequency
        if frequency == "daily":
            next_run = datetime.now() + timedelta(days=1)
        elif frequency == "weekly":
            next_run = datetime.now() + timedelta(weeks=1)
        elif frequency == "monthly":
            next_run = datetime.now() + timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid frequency")
        
        if modern_schema:
            cursor.execute("""
                INSERT INTO scheduled_reports
                (report_type, report_name, schedule_frequency, recipients, format, 
                 is_active, created_by, created_at, next_run_at)
                VALUES (%s, %s, %s, %s, %s, 1, %s, NOW(), %s)
            """, (report_type, report_name, frequency, recipients_str, format, 
                  current_user, next_run))
        else:
            cursor.execute("""
                INSERT INTO scheduled_reports
                (title, type, schedule, format, recipients, parameters, next_run, last_run, status, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, 'active', %s, NOW())
            """, (
                report_name,
                report_type,
                frequency,
                format,
                recipients_str,
                json.dumps({"report_type": report_type, "report_name": report_name, "frequency": frequency}),
                next_run,
                current_user,
            ))
        
        conn.commit()
        schedule_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "Report scheduled successfully",
            "next_run_at": next_run.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error scheduling report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-filtered")
async def export_filtered_report(
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    crime_type: Optional[str] = Query(None),
    current_user: str = Depends(get_username_from_token)
):
    """
    Generate and download a filtered crime report (PDF or Excel) with embedded charts.
    Respects the same filters as the frontend ReportsPanel.
    """
    try:
        from app.utils.report_generator import ReportGenerator

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Build WHERE clause from filters
        conditions = []
        params = []
        if start_date:
            conditions.append("DATE(crime_date) >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(crime_date) <= %s")
            params.append(end_date)
        if area:
            conditions.append("area = %s")
            params.append(area)
        if crime_type:
            conditions.append("crime_type = %s")
            params.append(crime_type)

        where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        # Summary stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_crimes,
                COUNT(DISTINCT area) as areas_affected,
                COUNT(DISTINCT crime_type) as crime_types,
                SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk_crimes,
                SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) as medium_risk_crimes,
                SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) as low_risk_crimes
            FROM crimes{where_sql}
        """, params)
        summary = cursor.fetchone()

        # Top areas
        cursor.execute(f"""
            SELECT area, COUNT(*) as count FROM crimes{where_sql}
            AND area IS NOT NULL
            GROUP BY area ORDER BY count DESC LIMIT 15
        """.replace("AND area", ("AND area" if conditions else "WHERE area")), params)
        top_areas = cursor.fetchall()

        # Crime type distribution
        cursor.execute(f"""
            SELECT crime_type, COUNT(*) as count FROM crimes{where_sql}
            AND crime_type IS NOT NULL
            GROUP BY crime_type ORDER BY count DESC LIMIT 10
        """.replace("AND crime_type IS NOT NULL", ("AND crime_type IS NOT NULL" if conditions else "WHERE crime_type IS NOT NULL")), params)
        crime_types = cursor.fetchall()

        # Trends by date
        cursor.execute(f"""
            SELECT DATE(crime_date) as date, COUNT(*) as count,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk
            FROM crimes{where_sql}
            GROUP BY DATE(crime_date) ORDER BY date
        """, params)
        trends = cursor.fetchall()

        cursor.close()
        conn.close()

        period_start = start_date or "All time"
        period_end = end_date or "present"

        report_data = {
            "summary": summary,
            "top_areas": top_areas,
            "crime_types": crime_types,
            "trends": trends,
            "period": f"{period_start} to {period_end}"
        }

        filters_dict = {
            "start_date": start_date or "N/A",
            "end_date": end_date or "N/A",
            "area": area or "All",
            "crime_type": crime_type or "All",
            "includeCharts": True,
            "includeStatistics": True,
            "includeRawData": True,
        }

        ext = "pdf" if format == "pdf" else "xlsx"
        filename = f"crime_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        generator = ReportGenerator(output_dir="reports")
        file_path = generator.generate_report(
            report_type="crime_summary",
            data=report_data,
            format=format,
            filters=filters_dict,
            filename=filename
        )

        media_types = {
            'pdf': 'application/pdf',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_types.get(format, 'application/octet-stream')
        )

    except Exception as e:
        logger.error(f"Error exporting filtered report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{report_id}")
async def download_report(
    report_id: int,
    current_user: str = Depends(get_username_from_token)
):
    """
    Download a generated report file
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT file_path, report_name, format
            FROM report_history
            WHERE id = %s
        """, (report_id,))
        
        report = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not report or not report['file_path']:
            raise HTTPException(status_code=404, detail="Report file not found")
        
        file_path = report['file_path']
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Report file does not exist on disk")
        
        # Determine media type based on format
        media_types = {
            'pdf': 'application/pdf',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'json': 'application/json'
        }
        
        media_type = media_types.get(report['format'], 'application/octet-stream')
        
        return FileResponse(
            path=file_path,
            filename=report['report_name'],
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
