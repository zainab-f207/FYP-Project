import sys
import os
import math
import urllib.parse
from typing import Any, Optional, Dict
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.utils.risk import get_risk_level, calculate_safety_score


# ── Public app base URL (update if domain changes) ────────────────────────────
# Use environment variable to allow local/network IP overrides
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://safevision.app").rstrip('/')


class EmailTemplates:
    """Professional SafeVision email alert templates."""

    # ─────────────────────────────── Shared helpers ───────────────────────────

    @staticmethod
    def _risk_pct(d: dict[str, Any]) -> float:
        rp_raw = d.get('risk_pct')
        if rp_raw is not None:
            r_pct = float(rp_raw)
        else:
            s_score = float(d.get('safety_score') or 50.0)
            r_pct = float(round(float(100.0 - s_score), 1)) # Ensure float cast for round argument
        # Manual round to 1 decimal place to avoid linting issues with builtin round()
        # The above calculation for r_pct already handles the rounding for the else branch.
        # The original code's manual rounding was for 'val', which is now 'r_pct' in the else branch.
        # Let's ensure consistency: if rp_raw is None, we calculate r_pct.
        # The original logic was:
        # val = 100.0 - float(d.get('safety_score') or 50.0)
        # val = max(1.0, min(99.0, val))
        # return float(math.floor(val * 10 + 0.5) / 10.0)
        # Let's apply this logic to r_pct if it was calculated from safety_score.
        if rp_raw is None:
            r_pct = max(1.0, min(99.0, r_pct))
            return float(math.floor(r_pct * 10 + 0.5) / 10.0)
        return r_pct


    @staticmethod
    def _clean_crime_name(name: Optional[str]) -> str:
        """Strips legalistic prefixes like 'Punishment for' from crime types."""
        if not name:
            return ""
        # Handle PPC style sections
        clean = name.replace('Punishment for ', '').replace('Punishment of ', '').replace('Offence of ', '').strip()
        # Handle common section numbers if present (e.g. "395 - Punishment for Dacoity")
        import re
        clean = re.sub(r'^\d+\s*-\s*', '', clean)
        # Title case if not empty
        if clean:
            return clean.capitalize() # Simplified as clean.capitalize() handles all cases correctly
        return name

    @staticmethod
    def _risk_meta(safety_score: float):
        level = get_risk_level(safety_score)
        if level == "Low":
            return "#16a34a", "🟢", "Low Risk"
        elif level == "Moderate":
            return "#d97706", "🟡", "Moderate Risk"
        elif level == "High":
            return "#dc2626", "🔴", "High Risk"
        else:  # Critical
            return "#991b1b", "🚨", "Critical Risk"

    @staticmethod
    def _advice_for_risk(risk_pct: float, is_home_work: bool = False) -> list[str]:
        """Return context-appropriate safety advice scaled to risk level."""
        area_label = "your registered area" if is_home_work else "this area"
        if risk_pct >= 81:
            return [
                f"<strong>Avoid {area_label}</strong> until the situation improves",
                "If you must travel here, go with a trusted group only",
                "Keep <strong>emergency numbers accessible</strong> (Police: 15, Rescue: 1122)",
                "Share your <strong>live location</strong> with family before entering",
                "Report any suspicious activity to authorities immediately",
                "Keep vehicle doors locked and windows up while driving through",
            ]
        elif risk_pct >= 51:
            return [
                f"Exercise <strong>extreme caution</strong> in {area_label}",
                "Avoid <strong>isolated streets and lanes</strong> especially after dark",
                "Prefer <strong>main, well-lit roads</strong> only",
                "Travel with a companion when possible",
                "Keep emergency numbers accessible (Police: 15, Rescue: 1122)",
                "Share your location with a trusted contact",
            ]
        elif risk_pct >= 21:
            return [
                f"<strong>Remain alert</strong> when traveling in {area_label}",
                "Prefer <strong>well-lit main roads</strong>; avoid isolated streets after dark",
                "Keep valuables out of sight and stay aware of your surroundings",
                "Note nearest police station / rescue point: Rescue 1122",
                "Trust your instincts — leave if a situation feels unsafe",
            ]
        else:
            return [
                "Maintain general <strong>situational awareness</strong>",
                "Keep valuables secure as a routine precaution",
                "Save emergency contacts (Police: 15, Rescue: 1122) in your phone",
            ]

    # ─────────────────────── Top crime type table HTML ────────────────────────

    @staticmethod
    def _top_crimes_table_html(top_crimes: list[dict[str, Any]], max_rows: int = 6) -> str:
        if not top_crimes:
            return ''
        rows = ''
        tc_list = list(top_crimes)
        for idx, tc in enumerate(tc_list):
            if idx >= max_rows:
                break
            ctype  = tc.get('crime_type', 'Unknown')
            count  = tc.get('count', 0)
            hc     = tc.get('high_count', 0)
            contrib = tc.get('risk_contribution', 'Low')
            if contrib == 'High':
                cc = '#dc2626'; ce = '🔴'
            elif contrib == 'Medium':
                cc = '#d97706'; ce = '🟠'
            else:
                cc = '#6b7280'; ce = '⚪'
            rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 14px;font-weight:600;color:#111827;">{ctype}</td>
          <td style="padding:10px 14px;text-align:center;font-weight:700;color:#374151;">{count}</td>
          <td style="padding:10px 14px;text-align:center;">
            <span style="background:{cc}18;color:{cc};padding:2px 10px;border-radius:12px;font-size:.85em;font-weight:700;">{ce} {contrib}</span>
          </td>
        </tr>"""
        return f"""
    <div style="margin:26px 0;">
      <h3 style="color:#111827;font-size:1.02em;margin:0 0 10px 0;">🔍 Top Risk Drivers in This Area <span style="font-size:.8em;color:#9ca3af;font-weight:400;">(last 365 days)</span></h3>
      <div style="overflow-x:auto;border-radius:10px;border:1px solid #e5e7eb;">
        <table style="width:100%;border-collapse:collapse;font-size:.89em;">
          <thead>
            <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb;">
              <th style="padding:10px 14px;text-align:left;color:#374151;">Incident Type</th>
              <th style="padding:10px 14px;text-align:center;color:#374151;">Count</th>
              <th style="padding:10px 14px;text-align:center;color:#374151;">Impact on Risk</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <p style="margin-top:8px;font-size:.78em;color:#9ca3af;font-style:italic;">* Impact is determined by severity (e.g., violent crimes have 2.5× higher impact on risk score than non-violent ones).</p>
    </div>"""

    @staticmethod
    def _top_crimes_text(top_crimes: list[dict[str, Any]], max_rows: int = 6) -> str:
        if not top_crimes:
            return ''
        lines = ['\nTOP RISK CRIMES (last 365 days):']
        tc_list = list(top_crimes)
        for idx, tc in enumerate(tc_list): # Changed to enumerate to avoid slice issues
            if idx >= max_rows:
                break
            ctype = tc.get('crime_type') or '?'
            count = tc.get('count') or 0
            contrib = tc.get('risk_contribution') or 'Low'
            lines.append(f"  • {ctype}  –  {count} incidents  ({contrib} risk)")
        return '\n'.join(lines)

    # ─────────────────────────── Sub-area table HTML ──────────────────────────

    @staticmethod
    def _subarea_row_html(s: dict[str, Any]) -> str:
        name  = s.get('name', 'Unknown')
        urdu  = s.get('urdu') or ''
        rl    = s.get('risk_level', 'Unknown')
        rp    = s.get('risk_pct')
        safe  = s.get('safety_score', 0)
        total = s.get('total', 0)
        pct   = f"{float(rp):.0f}%" if rp is not None else f"{round(100 - float(safe)):.0f}%"
        if rl == 'High':
            rc = '#dc2626'; re = '🔴'
        elif rl == 'Medium':
            rc = '#d97706'; re = '🟠'
        else:
            rc = '#16a34a'; re = '🟢'
        urdu_html = f'<div style="font-size:.76em;color:#9ca3af;">{urdu}</div>' if urdu else ''
        return f"""
        <tr style="border-bottom:1px solid #f3f4f6;">
          <td style="padding:10px 14px;">
            <div style="font-weight:600;color:#111827;">{name}</div>{urdu_html}
          </td>
          <td style="padding:10px 14px;text-align:center;">
            <span style="background:{rc}18;color:{rc};padding:2px 10px;border-radius:12px;font-size:.85em;font-weight:700;">{re} {rl}</span>
          </td>
          <td style="padding:10px 14px;text-align:center;font-weight:800;color:{rc};">{pct}</td>
          <td style="padding:10px 14px;text-align:center;color:#6b7280;font-size:.88em;">{total}</td>
        </tr>"""

    @staticmethod
    def _subarea_table_html(subareas: list[dict[str, Any]], max_rows: int = 10) -> str:
        if not subareas:
            return ''
        sa_list = list(subareas)
        rows = ''.join(EmailTemplates._subarea_row_html(s) for s in sa_list[:max_rows])
        return f"""
    <div style="margin:26px 0;">
      <h3 style="color:#111827;font-size:1.02em;margin:0 0 10px 0;">📍 Sub-Area Risk Breakdown <span style="font-size:.8em;color:#9ca3af;font-weight:400;">(last 365 days)</span></h3>
      <div style="overflow-x:auto;border-radius:10px;border:1px solid #e5e7eb;">
        <table style="width:100%;border-collapse:collapse;font-size:.89em;">
          <thead>
            <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb;">
              <th style="padding:10px 14px;text-align:left;color:#374151;">Sub-Area</th>
              <th style="padding:10px 14px;text-align:center;color:#374151;">Risk Level</th>
              <th style="padding:10px 14px;text-align:center;color:#374151;">Risk %</th>
              <th style="padding:10px 14px;text-align:center;color:#374151;">Incidents (365d)</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <p style="margin-top:8px;font-size:.78em;color:#9ca3af;font-style:italic;">* Overall risk reflects combined patterns across nearby blocks, not just individual sub-areas.</p>
    </div>"""

    @staticmethod
    def _subarea_text(subareas: list[dict[str, Any]], max_rows: int = 10) -> str:
        if not subareas:
            return ''
        lines = ['\nSUB-AREA RISK BREAKDOWN (last 365 days):']
        sa_list = list(subareas)
        for i, s in enumerate(sa_list[:max_rows], 1):
            rp = s.get('risk_pct')
            pct = f"{float(rp):.0f}%" if rp is not None else f"{100.0 - float(s.get('safety_score') or 50.0):.0f}%"
            lines.append(f"  {i}. {s.get('name','?')}  –  {pct} ({s.get('risk_level','-')}) | Incidents: {s.get('total',0)}")
        return '\n'.join(lines)

    # ──────────────────────── Risk methodology box ────────────────────────────

    @staticmethod
    def _methodology_box_html(risk_pct: float, total: int, high_risk: int, recent_7d: int, time_label: Optional[str]) -> str:
        """Small transparent info box explaining how the score was calculated."""
        return f"""
    <div style="margin:20px 0;padding:14px 18px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;">
      <p style="margin:0 0 8px;font-size:.88em;font-weight:700;color:#0369a1;">How Risk Is Calculated (Simplified)</p>
      <p style="font-size:.84em;color:#0c4a6e;margin-bottom:10px;">
        SafeVision combines observed incidents and time patterns to estimate current risk in your area.
      </p>
      <ul style="margin:0;padding-left:18px;font-size:.84em;color:#0c4a6e;line-height:1.8;">
        <li><strong>Incident frequency:</strong> how often crimes are reported.</li>
        <li><strong>Severity:</strong> violent and high-impact crimes are weighted higher.</li>
        <li><strong>Recency:</strong> recent incidents influence the score more strongly.</li>
        <li><strong>Time patterns:</strong> day/night variation is included in the estimate.</li>
      </ul>
    </div>"""

    # ─────────────────────── Alert trigger reason box ─────────────────────────

    @staticmethod
    def _trigger_box_html(reason: Optional[str], total: int, high_risk: int, risk_level: str) -> str:
        if not reason:
            return ''
        return f"""
    <div style="margin:18px 0;padding:14px 18px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;">
      <p style="margin:0 0 8px;font-size:.88em;font-weight:700;color:#c2410c;">🚨 Alert Trigger Summary</p>
      <p style="font-size:.85em;color:#7c2d12;margin-bottom:8px;">{reason}</p>
      <ul style="margin:0;padding-left:18px;font-size:.85em;color:#7c2d12;line-height:1.6;">
        <li><strong>{high_risk}</strong> severe incidents pinpointed in this area</li>
        <li><strong>{total}</strong> total recorded incidents driving the <strong>{risk_level}</strong> risk</li>
        <li>Elevated patterns detected for this specific time period</li>
      </ul>
    </div>"""

    # ──────────────────────── Map / navigation link ───────────────────────────

    @staticmethod
    def _map_link_html(area_name: str, lat: float = 0.0, lng: float = 0.0,
             email_token: str = "", user_id: int = 0) -> str:
        import urllib.parse
        BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
        slug = urllib.parse.quote_plus(area_name.lower().replace(' ', '-'))

        # Deep-link destinations (frontend routes). The dashboard router reads
        # `active=` (page tab) and `area=` / `to=` (context). Using `tab=` here
        # would land users on the default Dashboard instead of the intended page.
        map_next   = f"/dashboard?active=crime-map&area={slug}"
        route_next = f"/dashboard?active=navigation&to={slug}"
        pred_next  = f"/dashboard?active=prediction&area={slug}"

        def _wrap(next_path: str) -> str:
            """Wrap a frontend path in an email magic-link so user is auto-logged in."""
            if email_token:
                enc_next = urllib.parse.quote(next_path, safe='')
                return f"{BACKEND_URL}/api/auth/email-link?token={email_token}&next={enc_next}"
            # Fallback: direct link (user must be logged in)
            return f"{APP_BASE_URL}{next_path}"

        map_url  = _wrap(map_next)
        nav_url  = _wrap(route_next)
        pred_url = _wrap(pred_next)

        return f"""
    <div style="margin:22px 0;padding:14px 18px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;display:flex;gap:14px;flex-wrap:wrap;justify-content:center;">
      <a href="{map_url}" style="display:inline-block;background:#16a34a;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-size:.88em;font-weight:700;margin:5px;">🗺️ View on Map</a>
      <a href="{nav_url}" style="display:inline-block;background:#2563eb;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-size:.88em;font-weight:700;margin:5px;">🧭 Open Route</a>
      <a href="{pred_url}" style="display:inline-block;background:#8b5cf6;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-size:.88em;font-weight:700;margin:5px;">🔮 Predict Risk</a>
    </div>"""


    # ──────────────────────────── Shared CSS ─────────────────────────────────

    @staticmethod
    def _base_css(color: str) -> str:
        return f"""
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Roboto',sans-serif; background:#f3f4f6; color:#111827; line-height:1.6; }}
    .wrapper {{ max-width:660px; margin:24px auto; background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,.09); }}
    .header {{ background:linear-gradient(135deg,{color} 0%,{color}cc 100%); padding:36px 30px 26px; text-align:center; color:#fff; }}
    .header .badge {{ display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.3); padding:4px 14px; border-radius:20px; font-size:.76em; letter-spacing:.06em; text-transform:uppercase; margin-bottom:10px; }}
    .header h1 {{ font-size:2em; font-weight:800; margin:0 0 5px; }}
    .body {{ padding:28px 30px; }}
    .summary-card {{ background:#fafafa; border:1px solid #e5e7eb; border-left:5px solid {color}; border-radius:10px; padding:18px 20px; margin-bottom:22px; }}
    .metrics {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:22px; }}
    .metric {{ background:#f9fafb; border:1px solid #e5e7eb; border-radius:10px; padding:14px 8px; text-align:center; }}
    .metric .val {{ font-size:1.8em; font-weight:800; color:{color}; margin:3px 0; }}
    .metric .lbl {{ font-size:.72em; text-transform:uppercase; color:#9ca3af; letter-spacing:.05em; }}
    .actions {{ background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:16px 20px; margin:22px 0; }}
    .actions h3 {{ color:#1d4ed8; margin:0 0 10px; font-size:.98em; }}
    .actions li {{ margin:7px 0 7px 18px; color:#1e3a8a; font-size:.9em; }}
    .risk-pill {{ display:inline-block; background:{color}18; color:{color}; border:1px solid {color}44; padding:3px 12px; border-radius:18px; font-weight:700; }}
    .footer {{ background:#f9fafb; border-top:1px solid #e5e7eb; padding:18px 24px; text-align:center; font-size:.8em; color:#9ca3af; }}"""

    # ═══════════════════ HIGH RISK — home / work area ═════════════════════════

    @staticmethod
    def high_risk_alert_enhanced(alert_data: dict[str, Any]) -> dict[str, str]:
        """Enhanced high-risk alert for home / work registered areas with all 8 improvements."""
        safety_score = alert_data.get('safety_score')
        if safety_score is None:
            risk_pct = EmailTemplates._risk_pct(alert_data)
            safety_score = float(round(float(100.0 - float(risk_pct)), 1))
        else:
            safety_score = float(safety_score)
            risk_pct = float(round(float(100.0 - safety_score), 1))
            
        color, emoji, level_label = EmailTemplates._risk_meta(safety_score)
        risk_level   = alert_data.get('risk_level') or level_label.title()
        area_type    = (alert_data.get('area_type') or 'HOME').upper()
        area_name_raw = alert_data.get('area_name') or alert_data.get('address') or 'Location'
        area_name    = area_name_raw.split('(')[0].strip()
        area_translit = ''
        area_urdu    = ''
        dominant_crime = alert_data.get('dominant_crime') or ''
        subareas     = alert_data.get('subareas') or []
        top_crimes   = alert_data.get('top_crimes_list') or []
        recent_7d    = int(alert_data.get('recent_7d_crimes', 0))
        time_label   = alert_data.get('time_risk_label')
        trigger_reason = alert_data.get('alert_trigger_reason')
        no_recent_but_historical = bool(alert_data.get('no_recent_but_historical', False))
        timestamp    = alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        high_risk    = int(alert_data.get('high_risk_crimes', 0))
        medium_risk  = int(alert_data.get('medium_risk_crimes', 0))
        total        = int(alert_data.get('total_crimes', 0))
        total_365    = int(alert_data.get('total_crimes_365', total))
        unique_types = int(alert_data.get('unique_crime_types', 0))

        # Simplify Urdu name for consistency
        area_urdu = alert_data.get('area_urdu') or ''
        if area_urdu and ('،' in area_urdu or 'بلاک' in area_urdu):
             area_urdu = area_urdu.split('،')[0].split('بلاک')[0].strip()

        urdu_html = f'<p style="font-size:1.06em;font-weight:700;color:#1e3a8a;margin:5px 0;">{area_urdu}</p>' if area_urdu else ''

        area_label   = area_name

        # Set area-specific subjects for home vs work alerts
        if area_type == 'HOME':
            subject = "🏠 SafeVision Home Area Alert"
        elif area_type == 'WORK':
            subject = "🏢 SafeVision Work Area Alert"
        else:
            subject = "SafeVision Safety Alert"

        advice_items = EmailTemplates._advice_for_risk(risk_pct, is_home_work=True)
        advice_html  = ''.join(f'<li style="margin:7px 0 7px 18px;color:#1e3a8a;font-size:.9em;">{a}</li>' for a in advice_items)

        top_crimes_html  = EmailTemplates._top_crimes_table_html(top_crimes)
        subareas_html    = EmailTemplates._subarea_table_html(subareas)
        methodology_html = EmailTemplates._methodology_box_html(risk_pct, total, high_risk, recent_7d, time_label)
        trigger_html     = EmailTemplates._trigger_box_html(trigger_reason, total, high_risk, risk_level)
        map_html         = EmailTemplates._map_link_html(area_name, email_token=alert_data.get('email_token', ''))


        dom_html  = f'<p style="font-size:.88em;color:#6b7280;margin:5px 0 0;">📌 Most common: <strong>{dominant_crime}</strong></p>' if dominant_crime else ''
        time_badge = f'<span style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;padding:2px 10px;border-radius:12px;font-size:.8em;margin-left:8px;">⏰ {time_label}</span>' if time_label else ''
        level_norm = str(risk_level).lower()
        alert_line = "⚠️ CAUTION — Moderate Risk Detected" if ('moderate' in level_norm or 'caution' in level_norm or 'medium' in level_norm) else f"{emoji} {level_label} Risk Detected"
        why_recent_li = f'<li><strong>{total}</strong> incidents reported in the last 90 days</li>'
        if no_recent_but_historical:
            why_recent_li = f'<li>Recent activity is quiet (0 incidents in 90d) but <strong>historical risk</strong> remains significant ({total_365} past incidents)</li>'

        why_receiving_html = f"""
      <div style="margin:16px 0;padding:14px 16px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;">
        <p style="margin:0 0 8px;font-size:.9em;font-weight:700;color:#9a3412;">🚨 Why You're Receiving This Alert</p>
        <ul style="margin:0;padding-left:18px;font-size:.86em;color:#7c2d12;line-height:1.7;">
          {why_recent_li}
          <li><strong>{high_risk}</strong> high-severity incidents identified</li>
          <li>Increased activity detected for this time period</li>
          <li>Most frequent serious offense: <strong>{dominant_crime or 'Not specified'}</strong></li>
        </ul>
      </div>"""
        key_drivers_html = """
      <div style="margin:16px 0;padding:14px 16px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;">
        <p style="margin:0 0 8px;font-size:.9em;font-weight:700;color:#111827;">🔍 Key Risk Drivers (Last 12 Months)</p>
        <ul style="margin:0;padding-left:18px;font-size:.85em;color:#374151;line-height:1.7;">
          <li>Violent and high-impact crimes contributing disproportionately to risk</li>
          <li>Repeated incidents across multiple nearby blocks</li>
          <li>Time-based patterns showing elevated night risk</li>
        </ul>
      </div>"""
        area_insight_html = """
      <div style="margin:16px 0;padding:13px 16px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;">
        <p style="margin:0;font-size:.85em;color:#1e3a8a;"><strong>📍 Local Area Insights:</strong> While individual sub-areas may show low to moderate activity, the combined pattern across nearby blocks increases overall exposure risk.</p>
      </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision — {level_label}</title>
  <style>{EmailTemplates._base_css(color)}</style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="badge">SafeVision Safety Alert</div>
      <h1>{alert_line}</h1>
      <p style="opacity:.9;font-size:1.05em;">Your registered {area_type.lower()} area ({area_label}) is experiencing elevated risk levels, particularly during nighttime hours.{time_badge}</p>
    </div>
    <div class="body">

      {why_receiving_html}

      <div class="summary-card">
        <p style="font-size:1.08em;font-weight:700;">📍 {area_label}</p>
        {urdu_html}
        <p style="margin:6px 0;">Risk Score: <span class="risk-pill">{risk_pct:.0f}%</span> &nbsp;·&nbsp; Level: <strong>{risk_level}</strong></p>
        {dom_html}
        <p style="margin-top:8px;font-size:.82em;color:#9ca3af;">🕒 {timestamp}</p>
      </div>

      {methodology_html}
      {key_drivers_html}
      {area_insight_html}

      {top_crimes_html}

      {subareas_html}

      <div style="margin:18px 0;padding:14px 16px;background:#fef3c7;border-radius:10px;border:1px solid #fde68a;">
        <p style="font-size:.87em;color:#92400e;margin:0;"><strong>📋 Crime Summary (90d):</strong> {high_risk} high-risk · {medium_risk} medium-risk · {total} total incidents.</p>
        <p style="font-size:.82em;color:#92400e;margin:5px 0 0;"><strong>365d Context:</strong> {total_365} total incidents · {unique_types} distinct crime types.</p>
      </div>

      {map_html}

      <div class="actions">
        <h3>⚠️ Recommended Precautions</h3>
        <ul>{advice_html}</ul>
      </div>

    </div>
    <div class="footer">
      <p><strong>This is an automated alert based on real incident data and predictive analysis.</strong></p>
      <p>SafeVision Safety System © {datetime.now().year}</p>
    </div>
  </div>
</body>
</html>"""


        top_crimes_text  = EmailTemplates._top_crimes_text(top_crimes)
        subareas_text    = EmailTemplates._subarea_text(subareas)
        advice_text      = '\n'.join(f"  ✓ {a.replace('<strong>','').replace('</strong>','')}" for a in advice_items)
        trigger_text     = f"\n🔔 WHY THIS ALERT: {trigger_reason}\n" if trigger_reason else ''
        time_text        = f"⏰ Current period: {time_label}\n" if time_label else ''

        # Prepare plain-text 'Why' summary components
        why_recent_text = f"  {total} incidents reported in the last 90 days"
        if no_recent_but_historical:
            why_recent_text = f"  Recent activity is quiet (0 in 90d) but historical risk remains high ({total_365} past incidents)"

        text = f"""SafeVision Safety Alert

      {alert_line}
{trigger_text}
📍 {area_label}

🕒 {timestamp}
{time_text}
🎯 RISK SCORE   : {risk_pct:.0f}%  ({risk_level})
💯 SAFETY SCORE : {safety_score:.0f}%
🔴 HIGH-RISK (90d)   : {high_risk} incident(s)
🟡 MEDIUM-RISK (90d) : {medium_risk} incident(s)
📊 TOTAL (90d)       : {total}
📊 TOTAL (365d)      : {total_365}
 LAST 7 DAYS  : {recent_7d} incident(s)
🗂️ CRIME TYPES  : {unique_types} distinct categories
{"📌 TOP CRIME: " + dominant_crime if dominant_crime else ''}

WHY YOU'RE RECEIVING THIS ALERT
{why_recent_text}
  {high_risk} high-severity incidents identified
  Increased activity detected for this time period

HOW RISK IS CALCULATED (SIMPLIFIED)
  Uses incident frequency, severity, recency, and day/night patterns
  High-impact incidents influence the score more than low-impact incidents
  Recent activity is weighted more than old records
{top_crimes_text}
{subareas_text}

SAFETY RECOMMENDATIONS:
{advice_text}

🗺️ View Area Risk Map: {APP_BASE_URL}/dashboard?active=crime-map&area={area_name.lower().replace(' ', '-')}
🧭 Open Route        : {APP_BASE_URL}/dashboard?active=navigation&to={area_name.lower().replace(' ', '-')}
🔮 Predict Risk      : {APP_BASE_URL}/dashboard?active=prediction&area={area_name.lower().replace(' ', '-')}

This is an automated alert based on real incident data and predictive analysis.
"""
        return {"subject": subject, "html": html, "text": text}

    # ═══════════════════ LIVE LOCATION ALERT (SHORT & URGENT) ═════════════════
    
    @staticmethod
    def live_location_alert(alert_data: Dict[str, Any]) -> str:
        risk_level = alert_data.get('risk_level', 'High')
        risk_pct   = float(alert_data.get('risk_pct', 70.0))
        area_name_raw = alert_data.get('area_name_raw', 'Current Location')
        # Clean area name
        area_name = area_name_raw.split('(')[0].strip()
        
        dominant_crime = alert_data.get('dominant_crime') or 'Incidents of concern'
        # Support both legacy and current payload keys from alert_notifications.py
        total = int(alert_data.get('incidents_90d', alert_data.get('total_crimes', 0)) or 0)
        historical_total = int(alert_data.get('total_crimes_365', 0) or 0)
        high_risk = int(alert_data.get('high_risk_90d', alert_data.get('high_risk_crimes', 0)) or 0)
        time_label   = alert_data.get('time_risk_label', 'Night')
        trigger_reason = alert_data.get('alert_trigger_reason', 'Elevated crime activity detected')
        timestamp    = alert_data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
        
        # Identification Logic
        is_historical = "historical" in risk_level.lower() or "proximity" in trigger_reason.lower()
        subject = f"🚨 {'NEARBY HISTORICAL' if is_historical else 'LIVE'} ALERT — {risk_level.upper()} RISK DETECTED"
        header_title = "You have entered near to an historically high-risk area" if is_historical else "You have just entered a high-risk zone"
        
        # Formatting Vars
        color = "#92400e" if is_historical else "#b91c1c"
        bg_color = "#fef3c7" if is_historical else "#fee2e2"
        border_color = "#fbbf24" if is_historical else "#f87171"
        badge_bg = "#fef3c7" if is_historical else "#fee2e2"
        badge_text = "#92400e" if is_historical else "#b91c1c"

        radius_km = float(alert_data.get('radius_km', 1.0) or 1.0)
        radius_label = f"{radius_km:g}"

        # Why You're Seeing This Bullet Points
        why_bullets = ""
        if is_historical:
            why_bullets += f'<li style="margin-bottom:8px;">You are within {radius_label} km of a historically high-risk area ({historical_total} cases)</li>'
            why_bullets += f'<li style="margin-bottom:8px;">No high-severity incidents have been recorded recently (last 90 days)</li>'
        else:
            why_bullets += f'<li style="margin-bottom:8px;">Recently high-severity activity detected in your surroundings</li>'
            why_bullets += f'<li style="margin-bottom:8px;">Within {radius_label} km of <strong>{total}</strong> recent incidents</li>'
        
        why_bullets += f'<li style="margin-bottom:8px;">Risk level is elevated during <strong>{time_label}</strong> hours</li>'

        # Advice
        actions = ["Avoid stopping in isolated or dark areas", "Stay on main, well-lit roads", "Do not share ride details with strangers", "Keep phone accessible for emergency use"]
        actions_html = "".join([f'<li style="margin-bottom:8px; padding-left:18px; position:relative;"><span style="position:absolute; left:0; color:{color}; font-weight:bold;">•</span> {a}</li>' for a in actions])
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <style>
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f4f4f5; color:#18181b; line-height:1.5; margin:0; padding:20px; }}
    .card {{ max-width:500px; margin:0 auto; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 10px 25px rgba(0,0,0,0.1); border:1px solid #e2e8f0; }}
    .header {{ background:{color}; padding:28px 24px; text-align:center; color:#fff; }}
    .header h1 {{ font-size:1.45em; font-weight:900; margin:0; line-height:1.25; }}
    .badge {{ display:inline-block; padding:3px 12px; background:rgba(255,255,255,0.2); border-radius:6px; font-size:0.75em; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px; }}
    .content {{ padding:24px; }}
    .loc-box {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:15px; margin-bottom:20px; }}
    .loc-label {{ font-size:0.72em; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:4px; display:block; }}
    .loc-val {{ font-size:1.2em; font-weight:800; color:#0f172a; }}
    .intel-line {{ font-size:0.9em; color:#334155; margin-top:8px; border-top:1px solid #e2e8f0; padding-top:8px; line-height:1.5; }}
    .status-card {{ background:{bg_color}; border:1px solid {border_color}; border-radius:12px; padding:18px; text-align:center; margin-bottom:20px; }}
    .status-title {{ font-size:0.8em; font-weight:800; text-transform:uppercase; letter-spacing:0.05em; color:{color}; margin-bottom:4px; }}
    .status-val {{ font-size:2.4em; font-weight:900; color:{color}; line-height:1.1; }}
    .status-desc {{ font-size:0.9em; font-weight:800; color:{color}; text-transform:uppercase; }}
    .status-note {{ font-size:0.85em; margin-top:10px; color:{color}; opacity:0.8; font-weight:500; }}
    .bullet-section {{ margin-bottom:20px; }}
    .bullet-title {{ font-weight:800; color:#1f2937; margin-bottom:12px; font-size:0.95em; }}
    .bullet-list {{ margin:0; padding:0; list-style:none; font-size:0.9em; color:#4b5563; }}
    .bullet-list li {{ margin-bottom:10px; padding-left:18px; position:relative; }}
    .bullet-list li:before {{ content:'•'; position:absolute; left:0; color:{color}; font-weight:bold; }}
    .action-box {{ background:#18181b; border-radius:12px; padding:20px; color:#fff; }}
    .action-title {{ font-size:0.8em; font-weight:800; color:#a1a1aa; text-transform:uppercase; margin-bottom:12px; }}
    .btn-row {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px; }}
    .btn {{ display:block; text-decoration:none; text-align:center; padding:12px; border-radius:10px; font-weight:800; font-size:0.9em; }}
    .footer {{ text-align:center; font-size:0.75em; color:#71717a; margin-top:20px; border-top:1px solid #e2e8f0; padding-top:15px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="badge">LIVE ALERT — {risk_level.upper()}</div>
      <h1>{header_title}</h1>
    </div>
    <div class="content">
      <div class="loc-box">
        <span class="loc-label">📍 Current Location</span>
        <div class="loc-val">{area_name}</div>
        <div class="intel-line">
            <strong>📡 Within {radius_label} km radius:</strong><br/>
           {trigger_reason}
        </div>
        <div style="margin-top:12px; font-size:0.8em; font-weight:bold; color:{badge_text}; background:{badge_bg}; display:inline-block; padding:3px 12px; border-radius:15px;">
           ⏰ {time_label}
        </div>
      </div>

      <div class="status-card">
        <div class="status-title">Current Risk Status</div>
        <div class="status-val">{risk_pct:.1f}%</div>
        <div class="status-desc">{risk_level.upper()}</div>
        <div class="status-note">
           {"No recent incidents detected in your surroundings. However, this area has a notable history of crime." if is_historical else "Recent incident patterns detected in your immediate surroundings. High caution advised."}
        </div>
      </div>

      <div class="bullet-section">
        <div class="bullet-title">Why You're Seeing This</div>
        <ul class="bullet-list">
          {why_bullets}
        </ul>
      </div>

      <div class="action-box">
        <div class="action-title">⚡ What To Do NOW</div>
        <ul style="margin:0; padding:0 0 0 18px; font-size:0.9em; line-height:1.6; color:#e4e4e7;">
          {actions_html}
        </ul>
        <div style="margin-top:12px; border-top:1px solid #3f3f46; padding-top:10px; font-size:0.85em; font-weight:bold;">
          📞 Police: 15 | 🚑 Rescue: 1122
        </div>
      </div>

      <div class="btn-row">
        <a href="{APP_BASE_URL}/dashboard?active=crime-map" class="btn" style="background:{color}; color:#fff;">🗺️ Live Map</a>
        <a href="{APP_BASE_URL}/dashboard?active=navigation" class="btn" style="background:#fff; border:1px solid #d1d5db; color:#18181b;">🧭 Safer Route</a>
      </div>
    </div>
    <div class="footer">
      SafeVision Safety System • Automated Alert<br>
      © {datetime.now().year} SafeVision • {timestamp}
    </div>
  </div>
</body>
</html>"""

        text = f"""LIVE ALERT — {risk_level.upper()} RISK
You have just entered a high-risk zone

📍 Current Location
{area_name}

📡 {trigger_reason} — {dominant_crime} is the most frequent.

⏰ {time_label} (highest risk period)

⚠️ Current Risk Status
{risk_pct:.1f}%
{risk_level.upper()}

{ "No recent incidents detected in your surroundings. However, this area has a notable history of crime." if is_historical else "Recent incident patterns detected in your immediate surroundings. High caution advised." }

🚨 Why You're Seeing This
{why_bullets.replace('<li>','• ').replace('</li>', chr(10)).replace('<strong>','').replace('</strong>','')}
{high_risk} high-severity cases detected nearby
Risk level elevated during {time_label} (highest risk period)
⚡ What To Do NOW
{chr(10).join([a for a in actions])}
📞 Police: 15 | 🚑 Rescue: 1122
🧭 Quick Actions
🗺️ Live Map
🧭 Safer Route
SafeVision Safety System • Automated Alert

© {datetime.now().year} SafeVision • {timestamp}"""

        return {"subject": subject, "html": html, "text": text}

    # ═══════════════════ HIGH RISK — general monitored area ═══════════════════

    @staticmethod
    def high_risk_alert(alert_data: dict[str, Any]) -> dict[str, str]:
        """High-risk alert for any monitored / live location."""
        safety_score = alert_data.get('safety_score')
        if safety_score is None:
            risk_pct = EmailTemplates._risk_pct(alert_data)
            safety_score = float(round(float(100.0 - float(risk_pct)), 1))
        else:
            safety_score = float(safety_score)
            risk_pct = float(round(float(100.0 - safety_score), 1))
            
        color, emoji, level_label = EmailTemplates._risk_meta(safety_score)

        risk_level   = alert_data.get('risk_level', 'High')
        area_name_raw = alert_data.get('area_name') or alert_data.get('address') or 'Unknown Area'
        dominant_crime = EmailTemplates._clean_crime_name(alert_data.get('dominant_crime'))
        area_name    = area_name_raw.split('(')[0].strip()
        area_translit = ''
        area_urdu    = ''
        dominant_crime = alert_data.get('dominant_crime') or ''
        subareas     = alert_data.get('subareas') or []
        top_crimes   = alert_data.get('top_crimes_list') or []
        recent_7d    = int(alert_data.get('recent_7d_crimes', 0))
        time_label   = alert_data.get('time_risk_label')
        trigger_reason = alert_data.get('alert_trigger_reason')
        timestamp    = alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        high_risk    = int(alert_data.get('high_risk_crimes', 0))
        medium_risk  = int(alert_data.get('medium_risk_crimes', 0))
        total        = int(alert_data.get('total_crimes', 0))
        total_365    = int(alert_data.get('total_crimes_365', total))
        unique_types = int(alert_data.get('unique_crime_types', 0))

        # Simplify Urdu name for consistency
        area_urdu = alert_data.get('area_urdu') or ''
        if area_urdu and ('،' in area_urdu or 'بلاک' in area_urdu):
             area_urdu = area_urdu.split('،')[0].split('بلاک')[0].strip()

        urdu_html = f'<p style="font-size:1.06em;font-weight:700;color:#1e3a8a;margin:5px 0;">{area_urdu}</p>' if area_urdu else ''

        area_label = area_name
        subject    = "SafeVision Safety Alert"

        advice_items     = EmailTemplates._advice_for_risk(risk_pct)
        advice_html      = ''.join(f'<li style="margin:7px 0 7px 18px;color:#1e3a8a;font-size:.9em;">{a}</li>' for a in advice_items)
        top_crimes_html  = EmailTemplates._top_crimes_table_html(top_crimes)
        subareas_html    = EmailTemplates._subarea_table_html(subareas, max_rows=8)
        methodology_html = EmailTemplates._methodology_box_html(risk_pct, total, high_risk, recent_7d, time_label)
        trigger_html     = EmailTemplates._trigger_box_html(trigger_reason, total, high_risk, risk_level)
        map_html         = EmailTemplates._map_link_html(area_name, email_token=alert_data.get('email_token', ''))


        dom_html   = f'<p style="font-size:.88em;color:#6b7280;margin:5px 0 0;">📌 Most common: <strong>{dominant_crime}</strong></p>' if dominant_crime else ''
        time_badge = f'<span style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;padding:2px 10px;border-radius:12px;font-size:.8em;margin-left:8px;">⏰ {time_label}</span>' if time_label else ''
        level_norm = str(risk_level).lower()
        alert_line = "⚠️ CAUTION — Moderate Risk Detected" if ('moderate' in level_norm or 'caution' in level_norm or 'medium' in level_norm) else f"{emoji} {level_label} Risk Detected"
        no_recent_but_historical = bool(alert_data.get('no_recent_but_historical', False))
        why_recent_li = f'<li><strong>{total}</strong> incidents reported in the last 90 days</li>'
        if no_recent_but_historical:
            why_recent_li = f'<li>Recent activity is quiet (0 incidents in 90d) but <strong>historical risk</strong> remains significant ({total_365} past incidents)</li>'

        why_receiving_html = f"""
      <div style="margin:16px 0;padding:14px 16px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;">
        <p style="margin:0 0 8px;font-size:.9em;font-weight:700;color:#9a3412;">🚨 Why You're Receiving This Alert</p>
        <ul style="margin:0;padding-left:18px;font-size:.86em;color:#7c2d12;line-height:1.7;">
          {why_recent_li}
          <li><strong>{high_risk}</strong> high-severity incidents identified</li>
          <li>Increased activity detected for this time period</li>
          <li>Most frequent serious offense: <strong>{dominant_crime or 'Not specified'}</strong></li>
        </ul>
      </div>"""
        key_drivers_html = """
      <div style="margin:16px 0;padding:14px 16px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;">
        <p style="margin:0 0 8px;font-size:.9em;font-weight:700;color:#111827;">🔍 Key Risk Drivers (Last 12 Months)</p>
        <ul style="margin:0;padding-left:18px;font-size:.85em;color:#374151;line-height:1.7;">
          <li>Violent and high-impact crimes contributing disproportionately to risk</li>
          <li>Repeated incidents across multiple nearby blocks</li>
          <li>Time-based patterns showing elevated night risk</li>
        </ul>
      </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision — {level_label}</title>
  <style>{EmailTemplates._base_css(color)}</style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="badge">SafeVision Safety Alert</div>
      <h1>{alert_line}</h1>
      <p style="opacity:.9;font-size:1em;">Your monitored area ({area_label}) is experiencing elevated risk levels, particularly during nighttime hours.{time_badge}</p>
    </div>
    <div class="body">

      {why_receiving_html}

      <div class="summary-card">
        <p style="font-size:1.06em;font-weight:700;">📍 {area_label}</p>
        {urdu_html}
        <p style="margin:6px 0;">Risk Score: <span class="risk-pill">{risk_pct:.0f}%</span> &nbsp;·&nbsp; Level: <strong>{risk_level}</strong></p>
        {dom_html}
        <p style="margin-top:8px;font-size:.82em;color:#9ca3af;">🕒 {timestamp}</p>
      </div>

      {methodology_html}
      {key_drivers_html}

      {top_crimes_html}

      {subareas_html}

      <div style="margin:16px 0;padding:13px 16px;background:#fef3c7;border-radius:10px;border:1px solid #fde68a;">
        <p style="font-size:.86em;color:#92400e;margin:0;"><strong>📋 (90d):</strong> {high_risk} high-risk · {medium_risk} medium-risk · {total} total incidents.</p>
        <p style="font-size:.81em;color:#92400e;margin:5px 0 0;"><strong>365d Context:</strong> {total_365} incidents · {unique_types} crime types.</p>
      </div>

      {map_html}

      <div class="actions">
        <h3>⚠️ Recommended Precautions</h3>
        <ul>{advice_html}</ul>
      </div>

    </div>
    <div class="footer">
      <p><strong>This is an automated alert based on real incident data and predictive analysis.</strong></p>
      <p>SafeVision Safety System © {datetime.now().year}</p>
    </div>
  </div>
</body>
</html>"""

        top_crimes_text  = EmailTemplates._top_crimes_text(top_crimes)
        subareas_text    = EmailTemplates._subarea_text(subareas, max_rows=8)
        advice_text      = '\n'.join(f"  ✓ {a.replace('<strong>','').replace('</strong>','')}" for a in advice_items)
        trigger_text     = f"\n🔔 WHY THIS ALERT: {trigger_reason}\n" if trigger_reason else ''
        time_text        = f"⏰ Current period: {time_label}\n" if time_label else ''

        text = f"""SafeVision Safety Alert

      {alert_line}
{trigger_text}
📍 {area_label}

🕒 {timestamp}
{time_text}
🎯 RISK SCORE  : {risk_pct:.0f}%  ({risk_level})
💯 SAFETY SCORE: {safety_score:.0f}%
🔴 HIGH-RISK (90d)   : {high_risk} incident(s)
🟡 MEDIUM-RISK (90d) : {medium_risk} incident(s)
📊 TOTAL (90d)       : {total}
📊 TOTAL (365d)      : {total_365}
📅 LAST 7 DAYS : {recent_7d} incident(s)
🗂️ CRIME TYPES : {unique_types} distinct
{"📌 TOP CRIME: " + dominant_crime if dominant_crime else ''}

WHY YOU'RE RECEIVING THIS ALERT
  {total} incidents reported in the last 90 days
  {high_risk} high-severity incidents identified
  Increased activity detected for this time period

HOW RISK IS CALCULATED (SIMPLIFIED)
  Uses incident frequency, severity, recency, and day/night patterns
  High-impact incidents influence the score more than low-impact incidents
  Recent activity is weighted more than old records
{top_crimes_text}
{subareas_text}

SAFETY RECOMMENDATIONS:
{advice_text}

🗺️ View Area Risk Map: {APP_BASE_URL}/dashboard?active=crime-map&area={area_name.lower().replace(' ', '-')}
🧭 Open Route        : {APP_BASE_URL}/dashboard?active=navigation&to={area_name.lower().replace(' ', '-')}
🔮 Predict Risk      : {APP_BASE_URL}/dashboard?active=prediction&area={area_name.lower().replace(' ', '-')}

This is an automated alert based on real incident data and predictive analysis.
"""
        return {"subject": subject, "html": html, "text": text}

    @staticmethod
    def nearby_incident_alert(alert_data: dict[str, Any]) -> dict[str, str]:
        """Urgent notification for a new incident reported near user's areas."""
        area_name = alert_data.get('area_name') or 'Your Nearby Area'
        incident_type = alert_data.get('incident_type') or 'Incident'
        severity = str(alert_data.get('severity', 'Medium')).upper()
        distance = alert_data.get('distance_km', 1.0)
        location_type = alert_data.get('location_type', 'monitored') # 'home', 'work', 'current'
        timestamp = alert_data.get('timestamp', datetime.now().strftime('%H:%M:%S'))
        
        # Color and Emoji logic based on severity
        if severity in ['HIGH', 'CRITICAL']:
            color = "#dc2626"
            emoji = "🚨"
            level_label = "CRITICAL"
        else:
            color = "#d97706"
            emoji = "⚠️"
            level_label = "CAUTION"
            
        subject = f"{emoji} URGENT: New {incident_type} reported near your {location_type}"

        # Clean strings for HTML
        incident_type_clean = EmailTemplates._clean_crime_name(incident_type)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision — Nearby Incident</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#fefce8; color:#111827; }}
    .wrapper {{ max-width:500px; margin:20px auto; background:#fff; border-radius:16px; overflow:hidden; border:2px solid {color}; }}
    .header {{ background:{color}; padding:26px 20px; text-align:center; color:#fff; }}
    .header h1 {{ font-size:1.3em; font-weight:900; }}
    .body {{ padding:24px 20px; }}
    .alert-card {{ background:#fef2f2; border-radius:12px; padding:18px; border:1px solid {color}44; margin-bottom:20px; text-align:center; }}
    .incident-type {{ font-size:1.6em; font-weight:900; color:{color}; margin:10px 0; }}
    .meta-item {{ display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #f3f4f6; font-size:0.9em; }}
    .meta-label {{ color:#6b7280; font-weight:600; }}
    .meta-val {{ color:#111827; font-weight:700; }}
    .btn {{ display:block; width:100%; padding:14px; background:{color}; color:#fff; text-decoration:none; text-align:center; border-radius:10px; font-weight:700; margin-top:20px; }}
    .footer {{ padding:20px; text-align:center; font-size:0.75em; color:#9ca3af; background:#f9fafb; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>{emoji} PROXIMITY ALERT</h1>
      <p>A new incident was reported near your {location_type} area</p>
    </div>
    <div class="body">
      <p style="font-size:0.95em; color:#374151; margin-bottom:15px;">Safety update for your registered <strong>{location_type}</strong> location:</p>
      
      <div class="alert-card">
        <div style="font-size:0.8em; font-weight:800; color:#9ca3af; text-transform:uppercase;">NEW INCIDENT REPORTED</div>
        <div class="incident-type">{incident_type_clean}</div>
        <div style="background:{color}18; color:{color}; display:inline-block; padding:3px 12px; border-radius:20px; font-size:0.8em; font-weight:800;">{level_label} SEVERITY</div>
      </div>

      <div class="meta-item">
        <span class="meta-label">📍 Area</span>
        <span class="meta-val">{area_name}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">📏 Proximity</span>
        <span class="meta-val">Approx. {distance:.2f} km from you</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">🕒 Reported At</span>
        <span class="meta-val">{timestamp}</span>
      </div>

      <p style="margin-top:20px; font-size:0.88em; color:#4b5563; line-height:1.6;">
        This alert was triggered because a new incident was added to the database within your designated safety radius. Please stay alert if you are currently in this area.
      </p>

      <a href="{APP_BASE_URL}/dashboard?active=crime-map&area={urllib.parse.quote(area_name)}" class="btn">🛡️ Open Safety Map</a>

      <div style="margin-top:20px; text-align:center; font-size:0.85em; font-weight:800; color:{color};">
        Emergency: Police 15 | Rescue 1122
      </div>
    </div>
    <div class="footer">
      <p>SafeVision Safety System • Real-time Monitoring</p>
      <p>© {datetime.now().year} SafeVision • {timestamp}</p>
    </div>
  </div>
</body>
</html>"""

        text = f"""{emoji} URGENT PROXIMITY ALERT
New {incident_type_clean} reported near your {location_type}!

📍 Area: {area_name}
📏 Proximity: {distance:.2f} km
🕒 Time: {timestamp}
⚠️ Severity: {level_label}

WHAT TO DO:
- Maintain high situational awareness
- Avoid isolated spots near the reported area
- Keep emergency contacts ready (Police 15 | Rescue 1122)

View live map: {APP_BASE_URL}/dashboard?active=crime-map
"""
        return {"subject": subject, "html": html, "text": text}

    # ═══════════════════════════ SAFE AREA ════════════════════════════════════

    @staticmethod
    def safe_area_alert(alert_data: dict[str, Any]) -> dict[str, str]:
        """Safe area notification — now includes evidence statistics so users trust it."""
        safety_score = alert_data.get('safety_score')
        if safety_score is None:
            risk_pct = EmailTemplates._risk_pct(alert_data)
            safety_score = float(round(100.0 - risk_pct, 1))
        else:
            safety_score = float(safety_score)
            risk_pct = float(round(float(100.0 - safety_score), 1))
            
        color, emoji, level_label = EmailTemplates._risk_meta(safety_score)
        risk_level   = alert_data.get('risk_level') or level_label.title()
        area_name_raw = alert_data.get('area_name') or alert_data.get('address') or 'Location'
        area_name    = str(area_name_raw).split('(')[0].strip()
        area_translit = ''
        area_urdu    = ''
        total        = int(alert_data.get('total_crimes', 0))
        total_365    = int(alert_data.get('total_crimes_365', total))
        recent_7d    = int(alert_data.get('recent_7d_crimes', 0))
        time_label   = alert_data.get('time_risk_label')
        top_crimes   = alert_data.get('top_crimes_list') or []
        no_recent_but_historical = bool(alert_data.get('no_recent_but_historical', False))
        trigger_reason = alert_data.get('alert_trigger_reason')
        timestamp    = alert_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        area_type    = (alert_data.get('area_type') or 'CURRENT').upper()

        area_label = area_name

        # Set area-specific subjects for safe area alerts
        if area_type == 'HOME':
            subject = f"🏠✅ Safe Home Area — {area_label} ({risk_pct:.0f}% Risk)"
        elif area_type == 'WORK':
            subject = f"🏢✅ Safe Work Area — {area_label} ({risk_pct:.0f}% Risk)"
        else:
            subject = f"✅ Safe Area — {area_label} ({risk_pct:.0f}% Risk)"

        urdu_html = ''
        time_badge = f'<span style="background:#dcfce7;color:#166534;border:1px solid #bbf7d0;padding:2px 10px;border-radius:12px;font-size:.78em;margin-left:8px;">⏰ {time_label}</span>' if time_label else ''

        # Highest risk crime in the safe area (for evidence)
        top_crime_note = ''
        if top_crimes:
            tc0 = top_crimes[0]
            top_crime_note = f'<p style="font-size:.86em;color:#4b5563;margin:6px 0;">📌 Highest recorded crime: <strong>{tc0.get("crime_type","N/A")}</strong> ({tc0.get("count",0)} incidents)</p>'

        historical_calm_html = ''
        if no_recent_but_historical:
            historical_calm_html = (
                '<p style="font-size:.84em;color:#065f46;margin:8px 0 0;">'
                'No recent incidents were detected, but this area has meaningful historical activity over the last 365 days.'
                '</p>'
            )

        trigger_text_safe = f'<p style="font-size:.84em;color:#166534;margin:6px 0;font-style:italic;">{trigger_reason}</p>' if trigger_reason else ''
        map_html = EmailTemplates._map_link_html(area_name, email_token=alert_data.get('email_token', ''))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision — Safe Area</title>
  <style>{EmailTemplates._base_css(color)}</style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="badge">SafeVision Safety Alert</div>
      <h1>✅ Safe Area Confirmed</h1>
      <p style="opacity:.9;font-size:1em;">No elevated risk detected{time_badge}</p>
    </div>
    <div class="body">

      <div class="summary-card">
        <p style="font-size:1.08em;font-weight:700;">📍 {area_label}</p>
        {urdu_html}
        <p style="margin:8px 0;">Risk Level: <strong style="color:#15803d;">{risk_pct:.0f}%</strong> ({risk_level})
          &nbsp;·&nbsp; Safety Score: <strong style="color:#15803d;">{safety_score:.0f}%</strong></p>
        <p style="font-size:.82em;color:#9ca3af;margin-top:6px;">🕒 {timestamp}</p>
        {trigger_text_safe}
      </div>

      <!-- Evidence statistics so the user trusts the "safe" verdict -->
      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px 18px;margin:18px 0;">
        <p style="font-weight:700;color:#166534;margin:0 0 10px;">📊 Recent Activity (90d + 365d context):</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
          <div style="background:#fff;border:1px solid #bbf7d0;border-radius:8px;padding:12px;text-align:center;">
            <div style="font-size:1.8em;font-weight:800;color:#16a34a;">{total}</div>
            <div style="font-size:.74em;color:#9ca3af;text-transform:uppercase;">Total Incidents (90d)</div>
          </div>
          <div style="background:#fff;border:1px solid #bbf7d0;border-radius:8px;padding:12px;text-align:center;">
            <div style="font-size:1.8em;font-weight:800;color:#16a34a;">{total_365}</div>
            <div style="font-size:.74em;color:#9ca3af;text-transform:uppercase;">Total Incidents (365d)</div>
          </div>
        </div>
        {top_crime_note}
        {historical_calm_html}
        <p style="font-size:.8em;color:#4b5563;margin:10px 0 0;">
          Risk score of <strong>{risk_pct:.0f}%</strong> computed using Poisson probability model on 365-day incident data.
          Anything below 20% is classified as low-risk.
        </p>
      </div>

      {map_html}

      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 18px;margin-top:16px;">
        <p style="font-size:.88em;color:#166534;margin:0;">
          💡 <strong>Tip:</strong> Even in low-risk areas, keep valuables secure and stay situationally aware.
          Emergency contacts: Police 15 · Rescue 1122
        </p>
      </div>

    </div>
    <div class="footer">
      <p><strong>SafeVision Safety Alert System</strong></p>
      <p>Automated alert · © {datetime.now().year} SafeVision</p>
    </div>
  </div>
</body>
</html>"""

        time_text = f"⏰ Current period: {time_label}\n" if time_label else ''
        top_c_text = f"\n📌 Highest recorded crime: {top_crimes[0].get('crime_type','N/A')} ({top_crimes[0].get('count',0)} incidents)" if top_crimes else ''
        historical_calm_text = (
          "\n  ℹ️ No recent incidents were detected, but this area has meaningful historical activity over the last 365 days."
          if no_recent_but_historical else ""
        )

        text = f"""✅ Safe Area Confirmed

📍 {area_label}

🕒 {timestamp}
{time_text}
🎯 RISK SCORE  : {risk_pct:.0f}% — {risk_level}
💯 SAFETY SCORE: {safety_score:.0f}%

RECENT ACTIVITY — EVIDENCE THIS AREA IS SAFE:
  📊 Total incidents (90 days) : {total}
  📊 Total incidents (365 days): {total_365}
  📅 Last 7 days             : {recent_7d}
  {top_c_text}
  {historical_calm_text}
  ℹ️ Risk score calculated via Poisson model on 365-day incident density.
     Anything below 20% is classified as low-risk.

💡 Tip: Keep valuables secure and stay situationally aware.
   Emergency contacts: Police 15 · Rescue 1122

🗺️ View Area Map: {APP_BASE_URL}/dashboard?active=crime-map&area={urllib.parse.quote(area_name)}

Automated SafeVision alert.
"""
        return {"subject": subject, "html": html, "text": text}

    # ═══════════════════════ SCHEDULED SUMMARY ════════════════════════════════


    # ═══════════════════ NEW INCIDENT ALERT (URGENT & SPECIFIC) ═════════════════

    @staticmethod
    def new_incident_alert(alert_data: dict[str, Any]) -> dict[str, str]:
        """Urgent notification for a specific new incident near a user's area."""
        area_name_raw = alert_data.get('area_name') or alert_data.get('address') or 'Your Area'
        area_name = area_name_raw.split('(')[0].strip()
        incident_type = alert_data.get('incident_type') or 'Incident'
        severity = str(alert_data.get('severity', 'High')).upper()
        # Support for multiple incidents
        multiple_incidents = False
        incidents_list = alert_data.get('incidents_list') or []
        if len(incidents_list) > 1:
          multiple_incidents = True
        distance = alert_data.get('distance_km', 0.5)
        location_type = str(alert_data.get('location_type', 'home')).upper()
        timestamp = alert_data.get('timestamp', datetime.now().strftime('%H:%M'))
        
        # Risk snapshot data — guard against None
        risk_pct   = float(alert_data.get('risk_pct') or 70.0)
        high_risk_90d = int(alert_data.get('high_risk_crimes') or 0)
        total_90d  = int(alert_data.get('total_crimes') or 0)
        distance   = float(alert_data.get('distance_km') or 0.5)
        email_token = alert_data.get('email_token', '')
        
        color, emoji, level_label = EmailTemplates._risk_meta(100.0 - risk_pct)

        # Build magic-link button URLs (auto-login when token present)
        BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
        _area_slug  = urllib.parse.quote_plus(area_name.lower())

        def _btn_url(active: str, param: str = 'area') -> str:
            # Dashboard reads `?active=` for the page tab and `?area=` /
            # `?to=` for context. Using `tab=` lands users on the default page.
            next_path = f"/dashboard?active={active}&{param}={_area_slug}"
            if email_token:
                return f"{BACKEND_URL}/api/auth/email-link?token={email_token}&next={urllib.parse.quote(next_path, safe='')}"
            return f"{APP_BASE_URL}{next_path}"

        map_btn_url   = _btn_url('crime-map')
        route_btn_url = _btn_url('navigation', param='to')
        pred_btn_url  = _btn_url('prediction')

        
        incident_type_clean = EmailTemplates._clean_crime_name(incident_type)
        severity_color = "#dc2626" if severity in ['HIGH', 'CRITICAL'] else "#d97706"
        severity_emoji = "🔴" if severity in ['HIGH', 'CRITICAL'] else "🟠"

        if multiple_incidents:
          subject = f"🚨 Multiple Incidents Alert — {area_name}"
        else:
          subject = f"🚨 New Incident Alert — {area_name}"
        # Build HTML for multiple incidents if present
        if multiple_incidents:
          incidents_html = '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">'
          incidents_html += '<tr><th style="border:1px solid #e5e7eb;padding:6px 8px;background:#f3f4f6;">Type</th><th style="border:1px solid #e5e7eb;padding:6px 8px;background:#f3f4f6;">Time</th><th style="border:1px solid #e5e7eb;padding:6px 8px;background:#f3f4f6;">Severity</th></tr>'
          for inc in incidents_list:
            inc_type = inc.get('type', 'Incident')
            inc_time = inc.get('time', '')
            inc_sev = inc.get('severity', '')
            incidents_html += f'<tr><td style="border:1px solid #e5e7eb;padding:6px 8px;">{inc_type}</td><td style="border:1px solid #e5e7eb;padding:6px 8px;">{inc_time}</td><td style="border:1px solid #e5e7eb;padding:6px 8px;">{inc_sev}</td></tr>'
          incidents_html += '</table>'
        else:
          incidents_html = ''

        # Fix APP_BASE_URL fallback
        global APP_BASE_URL
        if 'APP_BASE_URL' not in globals() or not APP_BASE_URL:
          APP_BASE_URL = os.getenv('APP_BASE_URL', 'https://safevision.pk')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision — New Incident Alert</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f9fafb; color:#111827; line-height:1.6; }}
    .wrapper {{ max-width:600px; margin:20px auto; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 10px 25px rgba(0,0,0,0.1); border:1px solid #e5e7eb; }}
    .header {{ background:#111827; padding:28px 24px; text-align:center; color:#fff; }}
    .header h1 {{ font-size:1.4em; font-weight:900; letter-spacing:0.03em; margin-bottom:8px; color:#ef4444; }}
    .header p {{ font-size:0.95em; opacity:0.9; font-weight:500; }}
    .body {{ padding:28px 24px; }}
    .infographic {{ background:#fef2f2; border-left:4px solid #ef4444; padding:20px; border-radius:0 12px 12px 0; margin-bottom:24px; }}
    .info-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; }}
    .info-item {{ background:rgba(255,255,255,0.7); padding:10px; border-radius:8px; border:1px solid rgba(239, 68, 68, 0.1); }}
    .info-label {{ font-size:0.75em; color:#6b7280; font-weight:700; text-transform:uppercase; margin-bottom:2px; }}
    .info-val {{ font-size:1em; font-weight:800; color:#111827; }}
    .details-box {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:20px; margin-bottom:24px; }}
    .detail-row {{ display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #edf2f7; }}
    .detail-row:last-child {{ border-bottom:none; }}
    .detail-label {{ color:#64748b; font-weight:600; font-size:0.9em; }}
    .detail-val {{ color:#1e293b; font-weight:700; font-size:0.95em; }}
    .status-pill {{ background:{severity_color}1a; color:{severity_color}; padding:2px 10px; border-radius:20px; font-size:0.8em; font-weight:800; }}
    .action-header {{ font-size:0.9em; font-weight:800; color:#b91c1c; text-transform:uppercase; margin-bottom:12px; letter-spacing:0.05em; }}
    .actions-list {{ margin:0; padding-left:20px; color:#450a0a; font-size:0.95em; }}
    .actions-list li {{ margin-bottom:8px; }}
    .snapshot {{ background:#f1f5f9; border-radius:12px; padding:18px; margin-top:30px; border:1px solid #e2e8f0; }}
    .snap-grid {{ display:flex; gap:15px; margin-top:12px; }}
    .snap-item {{ flex:1; text-align:center; }}
    .snap-val {{ font-size:1.3em; font-weight:900; color:#334155; }}
    .snap-lbl {{ font-size:0.7em; color:#94a3b8; font-weight:700; text-transform:uppercase; margin-top:2px; }}
    .btn {{ display:inline-block; width:100%; padding:14px; background:#111827; color:#fff; text-decoration:none; text-align:center; border-radius:10px; font-weight:800; font-size:0.95em; margin-top:24px; transition:background 0.2s; }}
    .footer {{ background:#f9fafb; padding:20px; text-align:center; color:#94a3b8; font-size:0.8em; border-top:1px solid #f1f5f9; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>{'🚨 MULTIPLE INCIDENTS ALERT' if multiple_incidents else '🚨 NEW INCIDENT ALERT'} — NEAR YOUR {location_type}</h1>
      <p>{'Multiple high-risk incidents have just occurred' if multiple_incidents else 'A high-risk incident has just occurred'} near your {location_type.lower()}.</p>
    </div>
    
    <div class="body">
      <div class="infographic">
        <p style="font-weight:800; color:#b91c1c; font-size:1.1em; margin-bottom:4px;">📍 Location: {area_name}</p>
        <p style="font-size:0.9em; color:#7f1d1d; opacity:0.8;">📏 Proximity: Within ~{distance:.1f} km of your saved location</p>
        <p style="font-size:0.9em; color:#7f1d1d; opacity:0.8;">🕒 Reported at: {timestamp} (just now)</p>
      </div>

      <p class="action-header">⚠️ Incident Details</p>
      {incidents_html if multiple_incidents else f'''<div class="details-box">
        <div class="detail-row">
          <span class="detail-label">Type:</span>
          <span class="detail-val">{incident_type_clean}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Severity:</span>
          <span class="detail-val"><span class="status-pill">{severity_emoji} {severity.capitalize()}</span></span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Status:</span>
          <span class="detail-val" style="color:#16a34a;">● Recently reported</span>
        </div>
      </div>'''}

      <p class="action-header">🚨 What This Means For You</p>
      <ul class="actions-list">
        <li>This is a recent, nearby incident — risk is currently elevated</li>
        <li>Activity may still be ongoing in surrounding areas</li>
        <li>Extra caution is advised for the next few hours</li>
      </ul>

      <div style="background:#fffcf0; border:1px solid #fde68a; padding:18px; border-radius:12px; margin-top:24px;">
        <p class="action-header" style="color:#854d0e; margin-bottom:10px;">⚡ Immediate Precautions</p>
        <ul class="actions-list" style="color:#713f12;">
          <li>Avoid the immediate vicinity of the incident</li>
          <li>Delay non-essential travel if possible</li>
          <li>Stay on main, well-lit roads</li>
          <li>Inform family or trusted contacts of your status</li>
        </ul>
        <div style="margin-top:14px; text-align:center; font-weight:900; color:#854d0e; border-top:1px dashed #fde68a; padding-top:12px;">
          📞 Police: 15 | 🚑 Rescue: 1122
        </div>
      </div>

      <div class="snapshot">
        <p class="action-header" style="color:#475569; margin-bottom:4px;">📊 Area Context (Background)</p>
        <div class="snap-grid">
          <div class="snap-item" style="border-right:1px solid #e2e8f0; padding-right:10px;">
            <div class="snap-val" style="color:{color};">{risk_pct:.0f}%</div>
            <div class="snap-lbl">Risk Score</div>
          </div>
          <div class="snap-item" style="border-right:1px solid #e2e8f0; padding-right:10px;">
            <div class="snap-val">{total_90d}</div>
            <div class="snap-lbl">Incidents (90d)</div>
          </div>
          <div class="snap-item">
            <div class="snap-val">{high_risk_90d}</div>
            <div class="snap-lbl">High Severity</div>
          </div>
        </div>
      </div>

      <div style="display:flex; gap:10px; margin-top:10px;">
        <a href="{map_btn_url}" class="btn">🗺️ View Incident on Map</a>
        <a href="{route_btn_url}" class="btn" style="background:#2563eb;">🧭 Find Safer Route</a>
      </div>
      <a href="{pred_btn_url}" class="btn" style="background:#8b5cf6; margin-top:10px;">🔮 Check Nearby Risk</a>

      <div style="margin-top:30px; padding:15px; border-top:1px solid #f1f5f9;">
        <p class="action-header" style="color:#94a3b8; font-size:0.75em;">ℹ️ Why You Received This</p>
        <p style="margin:0; font-size:0.8em; color:#94a3b8;">This alert was triggered due to a new incident near your saved location.</p>
      </div>
    </div>
    
    <div class="footer">
      <p>SafeVision Safety System • Real-time Emergency Monitoring</p>
      <p>© {datetime.now().year} SafeVision • {timestamp}</p>
    </div>

  </div>
</body>
</html>"""

        if multiple_incidents:
            incidents_text = '\n'.join([
                f"- {inc.get('type', 'Incident')} at {inc.get('time', '')} (Severity: {inc.get('severity', '')})"
                for inc in incidents_list
            ])
            text = f"""🚨 MULTIPLE INCIDENTS ALERT — NEAR YOUR {location_type}

Multiple high-risk incidents have just occurred near your {location_type.lower()}.

📍 Location: {area_name}
📏 Proximity: Within ~{distance:.1f} km
🕒 Reported at: {timestamp} (just now)

⚠️ Incident Details
{incidents_text}

🚨 What This Means For You
- These are recent, nearby incidents — risk is currently elevated
- Activity may still be ongoing in surrounding areas
- Extra caution is advised for the next few hours

⚡ Immediate Precautions
- Avoid the immediate vicinity of the incidents
- Delay non-essential travel if possible
- Stay on main, well-lit roads
- Inform family or trusted contacts of your status

📞 Police: 15 | 🚑 Rescue: 1122

📊 Area Context (Background)
Risk Score: {risk_pct:.0f}% ({level_label})
Incidents (90d): {total_90d}
High Severity: {high_risk_90d}

View on Map: {APP_BASE_URL}/dashboard?active=crime-map
Safer Route: {APP_BASE_URL}/dashboard?active=navigation
"""
        else:
            text = f"""🚨 NEW INCIDENT ALERT — NEAR YOUR {location_type}

A high-risk incident has just occurred near your {location_type.lower()}.

📍 Location: {area_name}
📏 Proximity: Within ~{distance:.1f} km
🕒 Reported at: {timestamp} (just now)

⚠️ Incident Details
Type: {incident_type_clean}
Severity: {severity_emoji} {severity.capitalize()}
Status: Recently reported

🚨 What This Means For You
- This is a recent, nearby incident — risk is currently elevated
- Activity may still be ongoing in surrounding areas
- Extra caution is advised for the next few hours

⚡ Immediate Precautions
- Avoid the immediate vicinity of the incident
- Delay non-essential travel if possible
- Stay on main, well-lit roads
- Inform family or trusted contacts of your status

📞 Police: 15 | 🚑 Rescue: 1122

📊 Area Context (Background)
Risk Score: {risk_pct:.0f}% ({level_label})
Incidents (90d): {total_90d}
High Severity: {high_risk_90d}

View on Map: {APP_BASE_URL}/dashboard?active=crime-map
Safer Route: {APP_BASE_URL}/dashboard?active=navigation
"""
        return {"subject": subject, "html": html, "text": text}


    @staticmethod
    def weekly_safety_report(report_data: dict[str, Any]) -> dict[str, str]:
        """High-fidelity weekly safety summary report."""
        area_name = report_data.get('area_name', 'Your Area')
        stats = report_data.get('stats', {})
        trend = report_data.get('trend', 'Stable')
        
        # Trend UI mapping
        trend_map = {
            'Increasing': {'icon': '↑', 'label': 'Increasing Risk', 'color': '#dc2626'},
            'Decreasing': {'icon': '↓', 'label': 'Improving Safety', 'color': '#16a34a'},
            'Stable': {'icon': '→', 'label': 'Stable', 'color': '#64748b'}
        }
        t_cfg = trend_map.get(trend, trend_map['Stable'])
        
        # Risk meta
        safety_score = float(stats.get('safety_score', 50.0))
        color, emoji, level_label = EmailTemplates._risk_meta(safety_score)
        
        # Comparison logic
        total_curr = int(stats.get('total_7d', 0))
        total_prev = int(stats.get('total_prev', 0))
        diff = total_curr - total_prev
        diff_label = f"({'+' if diff >= 0 else ''}{diff} from last week)" if total_prev > 0 else "(no data for last week)"
        
        subject = f"📊 Safety Report: {level_label} in {area_name}"
        
        # Dynamic Advice based on incidents
        high_7d = int(stats.get('high_7d', 0))
        dynamic_advice = []
        if high_7d > 0:
            dynamic_advice.append(f"<strong>Recent high-severity activity:</strong> Avoid traveling late at night in {area_name} this week.")
        if diff > 3:
            dynamic_advice.append(f"<strong>Noticeable spike in frequency:</strong> Exercise heightened awareness in crowded public spaces.")
        
        # Fallback to generic if no dynamic advice generated
        if not dynamic_advice:
            all_advice = EmailTemplates._advice_for_risk(100.0 - safety_score, True)
            dynamic_advice = all_advice[:2] if all_advice else []
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>SafeVision Weekly Report</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; }}
    .wrapper {{ max-width:600px; margin:20px auto; background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 15px 35px rgba(0,0,0,0.05); border:1px solid #e2e8f0; }}
    .header {{ background:#111827; padding:35px 25px; text-align:center; color:#fff; }}
    .header h1 {{ font-size:1.4em; font-weight:900; letter-spacing:0.02em; margin-bottom:5px; }}
    .header p {{ font-size:0.8em; opacity:0.8; font-weight:600; text-transform:uppercase; letter-spacing:0.1em; }}
    .body {{ padding:30px 25px; }}
    .status-card {{ background:#f8fafc; border-radius:16px; padding:25px; margin-bottom:25px; text-align:center; border:1px solid #e2e8f0; }}
    .status-label {{ font-size:0.75em; color:#64748b; font-weight:700; text-transform:uppercase; margin-bottom:8px; display:block; }}
    .status-val {{ font-size:2.0em; font-weight:900; color:#111827; margin-bottom:5px; }}
    .status-sub {{ color:#64748b; font-size:0.95em; font-weight:500; margin-bottom:12px; }}
    .trend-pill {{ display:inline-block; padding:4px 14px; border-radius:20px; font-size:0.85em; font-weight:800; background:#fff; border:1px solid #e2e8f0; }}
    .section-title {{ font-size:0.85em; font-weight:800; color:#475569; text-transform:uppercase; margin:30px 0 15px 0; letter-spacing:0.05em; border-bottom:1px solid #f1f5f9; padding-bottom:8px; }}
    .stats-row {{ display: flex; gap: 15px; margin-bottom: 25px; }}
    .stat-box {{ flex: 1; background:#fff; border:1px solid #e2e8f0; padding:20px 15px; border-radius:14px; text-align:center; }}
    .stat-num {{ font-size:2.0em; font-weight:900; color:#111827; display:block; line-height:1; margin-bottom:5px; }}
    .stat-lbl {{ font-size:0.7em; color:#94a3b8; font-weight:700; text-transform:uppercase; }}
    .stat-diff {{ font-size:0.75em; color:#64748b; margin-top:5px; display:block; }}
    .obs-list {{ margin:0; padding:0; list-style:none; color:#334155; font-size:0.95em; }}
    .obs-list li {{ margin-bottom:15px; position:relative; padding-left:25px; }}
    .obs-list li:before {{ content:'•'; position:absolute; left:0; color:{color}; font-weight:bold; }}
    .interpretation {{ padding: 15px; background: {color}08; border-left: 4px solid {color}; border-radius: 8px; font-size: 0.95em; color: #334155; margin-bottom: 25px; }}
    .advice-box {{ background:#111827; padding:25px; border-radius:16px; margin-top:30px; color:#fff; }}
    .advice-title {{ font-weight:800; color:#94a3b8; font-size:0.75em; margin-bottom:15px; text-transform:uppercase; letter-spacing:0.05em; }}
    .btn {{ display:inline-block; width:100%; padding:15px; background:#111827; color:#fff; text-decoration:none; text-align:center; border-radius:12px; font-weight:800; font-size:0.95em; margin-top:10px; }}
    .footer {{ background:#f9fafb; padding:25px; text-align:center; color:#94a3b8; font-size:0.8em; border-top:1px solid #f1f5f9; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <p>Weekly Safety Summary</p>
      <h1>📍 {area_name}</h1>
    </div>
    <div class="body">
      <div class="status-card">
        <span class="status-label">Overall Safety Profile</span>
        <div class="status-val">{emoji} {level_label}</div>
        <p class="status-sub">Safety Score: <strong>{safety_score:.0f}%</strong> (stable)</p>
        <div class="trend-pill" style="color:{t_cfg['color']}; border-color:{t_cfg['color']}30;">
          {t_cfg['icon']} {t_cfg['label']}
        </div>
      </div>

      <div class="interpretation">
        <strong>Report Analysis:</strong> Your area currently holds a <strong>{level_label.lower()}</strong> rating. {report_data.get('obs_trend', 'Patterns remain consistent.')}
      </div>

      <p class="section-title">📊 Activity (Last 7 Days)</p>
      <div class="stats-row">
        <div class="stat-box">
          <span class="stat-num">{total_curr}</span>
          <span class="stat-lbl">Incidents Reported</span>
          <span class="stat-diff">{diff_label}</span>
        </div>
        <div class="stat-box">
          <span class="stat-num">{high_7d}</span>
          <span class="stat-lbl">High Severity Cases</span>
          <span class="stat-diff">Verified incidents</span>
        </div>
      </div>

      <p class="section-title">⚠️ Key Observations</p>
      <ul class="obs-list">
        <li><strong>Trend:</strong> {report_data.get('obs_trend')}</li>
        <li><strong>Coverage:</strong> Verified incidents within your custom safety radius and immediate vicinity.</li>
        <li><strong>Time Context:</strong> Nighttime remains the highest risk period for {area_name}; situational awareness is advised.</li>
      </ul>

      <div class="advice-box">
        <p class="advice-title">💡 Data-Driven Decision Support</p>
        <ul class="obs-list" style="margin-bottom:0; color:#e2e8f0;">
          {"".join([f"<li>{adv}</li>" for adv in dynamic_advice])}
          <li>Share your movements with a trusted contact before travel.</li>
        </ul>
      </div>

      <div style="margin-top:30px;">
        <a href="{APP_BASE_URL}/dashboard?active=prediction&area={urllib.parse.quote(area_name)}" class="btn">Explore Detailed Trends</a>
        <a href="{APP_BASE_URL}/dashboard?active=navigation&to={urllib.parse.quote(area_name)}" class="btn" style="background:#fff; color:#111827; border:1px solid #e2e8f0;">Check Safe Routes</a>
      </div>
    </div>
    <div class="footer">
      <p>Empowering Smarter Decisions with Safety Intelligence</p>
      <p>© {datetime.now().year} SafeVision • Analytics based on real incident data</p>
    </div>
  </div>
</body>
</html>"""
        
        text = f"""📊 Weekly Safety Report — {area_name}
        
OVERALL STATUS: {emoji} {level_label} ({safety_score:.0f}%)
Comparison: {diff_label}

STATS (LAST 7 DAYS):
- Total Incidents: {total_curr}
- High Severity: {high_7d}

OBSERVATIONS:
- {report_data.get('obs_trend')}

ADVICE:
Visit {APP_BASE_URL}/dashboard for detailed insights.
"""
        return {"subject": subject, "html": html, "text": text}
