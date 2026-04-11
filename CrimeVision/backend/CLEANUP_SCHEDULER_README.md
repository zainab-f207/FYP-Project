# CrimeVision Account Cleanup Scheduler

## Overview
This automated scheduler deletes expired unverified user accounts and notifies the SuperAdmin.

## Features
- Runs every 6 hours automatically
- Deletes accounts where:
  - `is_verified = FALSE`
  - `token_expires_at < NOW()` (verification link expired)
- Sends detailed email notification to SuperAdmin with list of deleted accounts
- Logs all operations for audit trail

## Setup

### 1. Install Required Dependencies
```bash
pip install schedule
```

### 2. Set Environment Variables
Add the following to your `.env` file:

```env
# SuperAdmin Email (receives notifications about deleted accounts)
SUPER_ADMIN_EMAIL=admin@crimevision.com

# Email Configuration (already configured in email_verification.py)
AUTH_EMAIL_USERNAME=safevision.noreply@gmail.com
AUTH_EMAIL_PASSWORD=your_app_password_here
```

### 3. Run the Scheduler

#### Option 1: Run as a standalone process
```bash
cd backend
python -m app.cleanup_unverified_accounts
```

#### Option 2: Run as a background service (Linux/Mac)
```bash
nohup python -m app.cleanup_unverified_accounts &
```

#### Option 3: Run as a Windows service
Use a tool like NSSM (Non-Sucking Service Manager) to run it as a Windows service.

#### Option 4: Add to system startup
Add the script to your system's startup/cron jobs.

**Linux (crontab):**
```bash
@reboot cd /path/to/backend && python -m app.cleanup_unverified_accounts
```

**Windows (Task Scheduler):**
Create a new task that runs on system startup with the command:
```
python C:\path\to\backend\app\cleanup_unverified_accounts.py
```

## How It Works

1. **Scheduled Execution**: The scheduler runs every 6 hours
2. **Account Detection**: Finds all unverified accounts with expired tokens
3. **Account Deletion**: Deletes the expired accounts from the database
4. **Admin Notification**: Sends an email to SuperAdmin with:
   - Total number of deleted accounts
   - Detailed table with username, email, name, creation date, and expiration date
5. **Logging**: All operations are logged for monitoring

## Monitoring

Check the logs to monitor the scheduler:
```bash
# View real-time logs
tail -f logs/cleanup.log

# Check for errors
grep "ERROR" logs/cleanup.log
```

## Testing

To test the cleanup immediately without waiting 6 hours:
```python
from app.cleanup_unverified_accounts import cleanup_expired_unverified_accounts
cleanup_expired_unverified_accounts()
```

## Email Notification Sample

SuperAdmin will receive an email like this:

**Subject:** 🗑️ CrimeVision: 3 Unverified Account(s) Deleted

**Body:**
```
⚠️ Unverified Accounts Cleanup Report

Dear SuperAdmin,

The automated cleanup process has deleted 3 expired unverified user account(s) from the CrimeVision system.

These accounts failed to complete email verification within the 24-hour window and have been automatically removed.

Deleted Accounts:
┌──────────────┬─────────────────────┬──────────────┬─────────────────────┬─────────────────────┐
│ Username     │ Email               │ Name         │ Created At          │ Token Expired At    │
├──────────────┼─────────────────────┼──────────────┼─────────────────────┼─────────────────────┤
│ john.doe123  │ john@example.com    │ John Doe     │ 2025-11-24 10:00:00 │ 2025-11-25 10:00:00 │
│ jane.smith456│ jane@example.com    │ Jane Smith   │ 2025-11-24 11:30:00 │ 2025-11-25 11:30:00 │
│ test.user789 │ test@example.com    │ Test User    │ 2025-11-24 12:15:00 │ 2025-11-25 12:15:00 │
└──────────────┴─────────────────────┴──────────────┴─────────────────────┴─────────────────────┘

Note: This is an automated notification from the CrimeVision account cleanup system.
The cleanup process runs every 6 hours to maintain database hygiene.
```

## Troubleshooting

### Scheduler not running
- Check if Python process is running: `ps aux | grep cleanup_unverified_accounts`
- Check logs for errors
- Verify database connection settings

### Emails not sending
- Verify SMTP credentials in `.env`
- Check email logs
- Ensure SUPER_ADMIN_EMAIL is set correctly

### Accounts not being deleted
- Verify database schema has required columns
- Check if accounts actually have expired tokens
- Review logs for SQL errors

## Security Notes

- The scheduler only deletes accounts that are both unverified AND have expired tokens
- Verified accounts are never touched by this process
- All deletions are logged with full details
- SuperAdmin is always notified of deletions
