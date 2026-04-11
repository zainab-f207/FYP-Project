# Todo: Fix SyntaxError in email_templates.py

## Plan Status
- [x] User approved edit plan
- [ ] Create Todo.md ✅ **DONE**
- [ ] Fix unterminated f-string in `high_risk_alert_enhanced()`
- [ ] Remove duplicate `_map_link_html` method  
- [ ] Validate/clean all f-strings & formatting
- [ ] Test Python syntax: `python -m py_compile CrimeVision/backend/app/email_templates.py`
- [ ] Test import chain: `python -c "from app.email_templates import EmailTemplates; print('✅ Fixed')"`
- [ ] Restart uvicorn server
- [ ] Verify no more SyntaxError in logs
- [ ] Test email template generation
- [x] Mark complete with `attempt_completion`

## Commands to Run After Each Step:
```
# Test syntax
python -m py_compile "CrimeVision/backend/app/email_templates.py"

# Test import  
cd "CrimeVision/backend"
python -c "from app.email_templates import EmailTemplates; print('✅ Import OK')"

# Restart server (in backend dir)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

