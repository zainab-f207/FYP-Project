import asyncio
from datetime import datetime
from app.email_templates import EmailTemplates

def main():
    alert_data = {
        'username': 'high_risk_tester',
        'area_name': 'DHA Phase 4',
        'address': 'DHA Phase 4',
        'safety_score': 44,
        'risk_pct': 56,
        'risk_level': 'High',
        'total_crimes': 890,
        'high_risk_crimes': 15,
        'dominant_crime': 'Robbery',
        'alert_trigger_reason': 'Elevated risk detected during transit',
        'time_risk_label': 'Night',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Render the alert template
    rendered = EmailTemplates.live_location_alert(alert_data)
    
    with open('test_live_alert.html', 'w', encoding='utf-8') as f:
        f.write(rendered['html'])
        
    print("Successfully rendered live location alert to test_live_alert.html")

if __name__ == "__main__":
    main()
