# 🔐 Simple JWT Secret Key Setup

## Quick Setup (2 commands)

1. **Generate and set up your secret key:**
   ```bash
   python quick_setup.py
   ```

2. **Restart your FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

## What happens:

- ✅ Generates a 64-character secure random secret key
- ✅ Creates/updates your `.env` file automatically
- ✅ Your `auth.py` will use this secure key instead of the default

## Files involved:

- `auth_updated.py` - Your updated auth module with secure key generation
- `quick_setup.py` - Simple setup script (run this once)
- `.env` - Your environment file (created automatically)

## Security:

- 🔐 **64-character** cryptographically secure key
- 🔄 **Auto-generated** using Python's `secrets` module
- ⚠️ **Never commit** your `.env` file to version control

## Testing:

After setup, you should see in your server logs:
```
🔐 Using JWT Secret Key: abc123def456...xyz789 (Length: 64)
```

That's it! Your JWT authentication now uses a secure random secret key.
