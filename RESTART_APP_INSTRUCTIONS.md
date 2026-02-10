# How to Apply the Duplicate Click Fix

## The Problem
The deduplication code has been added to `routes/links.py`, but your Flask app is still running the **old code** from memory. You need to restart the app for changes to take effect.

## Solution: Restart Your Flask App

### Step 1: Stop the Current App
If your app is running, stop it by pressing:
- **Ctrl + C** in the terminal where Flask is running

### Step 2: Start the App Again
```bash
python app.py
```

Or if you're using Flask run:
```bash
flask run
```

### Step 3: Test the Fix
1. Open a link from your browser
2. Immediately refresh the page (within 10 seconds)
3. Check analytics - should show **1 click**, not 2

## How to Verify It's Working

Run this command AFTER restarting and clicking a link:
```bash
python debug_visits.py
```

Look for this message:
- ✅ **"No duplicate visits found"** = Fix is working!
- ⚠️ **"DUPLICATE DETECTED (< 10 seconds)"** = App not restarted or code issue

## What the Fix Does

The deduplication logic checks:
```python
# Has this same IP visited this link in the last 10 seconds?
recent_visit = query_db(
    """
    SELECT id FROM visits
    WHERE link_id = ? AND ip_hash = ?
    AND datetime(ts) > datetime(?, '-10 seconds')
    LIMIT 1
    """,
    [link["id"], ip_hash, now.isoformat()],
    one=True
)

if recent_visit:
    # Skip logging, but still redirect properly
    # (This is a duplicate/prefetch request)
```

## Important Notes

1. **Old visits remain in database** - The fix only affects NEW visits after restart
2. **10-second window** - Visits more than 10 seconds apart are counted separately (this is intentional)
3. **Same IP only** - Different IPs are always counted separately

## If Still Showing 2 Clicks

### Check 1: Is the app restarted?
```bash
# Look for this in terminal after restart:
 * Running on http://127.0.0.1:5000
 * Restarting with stat
```

### Check 2: Are you testing correctly?
- Click once from WhatsApp
- Wait for page to load completely
- Check analytics immediately
- Should show 1 click

### Check 3: Check the debug log
After clicking, check what's being captured:
```bash
type referrer_debug.txt
```

Look at the timestamps - if they're within 10 seconds, the second one should have been blocked.

## Clean Database (Optional)

If you want to start fresh and remove all old duplicate visits:

```python
# WARNING: This deletes ALL visits!
import sqlite3
conn = sqlite3.connect('smart_links.db')
conn.execute('DELETE FROM visits')
conn.commit()
conn.close()
```

Then restart the app and test with fresh clicks.

## Expected Behavior After Fix

✅ **Single click from WhatsApp** → 1 visit logged
✅ **Refresh within 10 seconds** → Still 1 visit (duplicate blocked)
✅ **Click again after 15 seconds** → 2 visits (legitimate revisit)
✅ **Different person clicks** → Each person counted separately

## Need Help?

If still showing duplicates after restart:
1. Check `referrer_debug.txt` for timestamps
2. Run `python debug_visits.py` to see visit patterns
3. Verify the deduplication code is in `routes/links.py` around line 293
