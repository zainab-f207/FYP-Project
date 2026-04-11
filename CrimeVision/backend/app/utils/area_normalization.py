import re
from typing import Optional


def canonicalize_area_query(area: Optional[str]) -> str:
    """Return a normalized area token for loose matching across area variants.

    Examples:
    - "Gulberg, Lahore" -> "gulberg"
    - " gulberg " -> "gulberg"
    """
    if not area:
        return ""
    text = str(area).strip().replace("،", ",")
    text = re.sub(r"\s+", " ", text)
    first_segment = text.split(",", 1)[0].strip()
    return first_segment.casefold()


def area_like_pattern(area: Optional[str]) -> str:
    key = canonicalize_area_query(area)
    return f"%{key}%" if key else "%"


def normalize_area_name(area_name: str) -> str:
    """Universal normalization for DHA areas and other sub-sectors."""
    if not area_name or area_name == "Unknown":
        return area_name
        
    _an_lower = area_name.lower().strip()
    
    # Don't normalize Bahria Town or other major brands to DHA
    if "bahria" in _an_lower:
        return area_name
        
    # Aggressively handle DHA Phases (e.g., 'Sec FF Ph 4', 'Phase 4 Block F...', 'DHA Phase 4')
    if "phase" in _an_lower or " ph " in _an_lower or _an_lower.endswith(" ph") or " ph:" in _an_lower or " ph." in _an_lower:
        _phase_trigger = "phase" if "phase" in _an_lower else "ph"
        _parts = _an_lower.split(_phase_trigger)
        if len(_parts) > 1:
            # Extract just the number, strip anything after it (Road, Block, etc.)
            _suffix = _parts[1].strip()
            # Handle cases like "ph 4", "ph: 4", "ph. 4"
            _suffix = _suffix.replace(":", "").replace(".", "").strip()
            _num_match = re.match(r'^(\d+)', _suffix)
            if _num_match:
                return f"DHA Phase {_num_match.group(1)}"
            elif _suffix:
                # Fallback to first word if not direct digit (e.g. roman numerals IV, V)
                _num = _suffix.split()[0].strip()
                if _num: return f"DHA Phase {_num.upper()}"
                
    # Handle common abbreviations like 'DHA Sec FF' -> 'DHA' if needed, but usually 
    # the Phase is what we want to aggregate by.
    if _an_lower.startswith("dha "):
        # If it's something like "DHA Block X" and no phase mentioned, keep it "DHA Phase X" might be hard, 
        # so just return the original if it didn't match the Phase pattern.
        return area_name
        
    return area_name
