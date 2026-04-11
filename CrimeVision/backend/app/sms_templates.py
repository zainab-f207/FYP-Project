# sms_templates.py
from typing import Any, Dict


class SMSTemplates:
    """SMS message templates for different alert types"""
    
    @staticmethod
    def high_risk_sms(alert_data: Dict[str, Any]) -> str:
        """High risk zone SMS alert with area details"""
        area_name = alert_data.get('area_name', 'Your area')
        coordinates = f"({alert_data.get('latitude', 'N/A')}, {alert_data.get('longitude', 'N/A')})"
        
        base_message = (
            f"🚨 CrimeVision Alert: {alert_data.get('risk_level', 'High')} risk at {area_name} {coordinates}. "
            f"Safety: {alert_data.get('safety_score', 0)}%. "
        )
        
        # Add incident info if available
        if alert_data.get('recent_incidents', 0) > 0:
            base_message += f"{alert_data.get('recent_incidents')} recent incidents. "
        
        base_message += "Stay alert, avoid isolated areas."
        
        return base_message

    @staticmethod
    def safe_area_sms(alert_data: Dict[str, Any]) -> str:
        """Safe area SMS alert with location details"""
        area_name = alert_data.get('area_name', 'Your area')
        coordinates = f"({alert_data.get('latitude', 'N/A')}, {alert_data.get('longitude', 'N/A')})"
        
        return (
            f"✅ CrimeVision: {area_name} {coordinates} is secure. "
            f"Safety: {alert_data.get('safety_score', 85)}%. "
            f"Risk: {alert_data.get('risk_level', 'Low')}. Area safe for normal activities."
        )
    
    @staticmethod
    def scheduled_alert_sms(alert_data: Dict[str, Any]) -> str:
        """Scheduled offline alert SMS"""
        return (
            f"📊 Safety Report: Your monitored areas are currently safe. "
            f"Home: {alert_data.get('home_safety_score', 85)}%, Work: {alert_data.get('work_safety_score', 78)}%. "
            f"Stay safe! - CrimeVision"
        )
    
    @staticmethod
    def immediate_risk_sms(alert_data: Dict[str, Any]) -> str:
        """Immediate risk SMS for live location alerts"""
        return (
            f"⚠️ IMMEDIATE ALERT: Entering high-risk zone. Safety: {alert_data.get('safety_score', 0)}%. "
            f"Consider alternative route. Stay in populated areas. - CrimeVision"
        )
