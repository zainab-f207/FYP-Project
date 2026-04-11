import sys
with open('../backend/main.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_signature = '''def api_me_stats_alias(
    current_user: Optional[str] = Depends(get_username_from_token),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None)
):'''

new_signature = '''def api_me_stats_alias(
    current_user: Optional[str] = Depends(get_username_from_token),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    area: Optional[str] = Query(None)
):'''

text = text.replace(old_signature, new_signature)

old_logic = '''            # 2. TIER 2: Neighborhood Fallback (Area Name from DB)
            if not current_stats or current_stats.get("total_crimes", 0) == 0:
                if nearest_db_area:
                    area_name = nearest_db_area
                    search_pattern = f"%{area_name}%"'''

new_logic = '''            # 2. TIER 2: Neighborhood Fallback (Area Name from DB or Client)
            if not current_stats or current_stats.get("total_crimes", 0) == 0:
                fallback_area = area or nearest_db_area
                if fallback_area:
                    area_name = fallback_area.strip()
                    search_pattern = f"%{area_name}%"'''

text = text.replace(old_logic, new_logic)

with open('../backend/main.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated main.py')
