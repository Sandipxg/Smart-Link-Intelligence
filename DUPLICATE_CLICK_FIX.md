# Duplicate Click Prevention Fix

## Problem
When opening links from WhatsApp (and other social media apps), the system was counting **2 clicks** instead of 1.

## Root Cause
Social media apps like WhatsApp, Facebook, Instagram, and Twitter make **multiple requests** when you share a link:

1. **Prefetch/Preview Request** - Made automatically to generate link preview/thumbnail
2. **Actual Click Request** - Made when user actually clicks the link

Both requests come from the same IP address within seconds of each other, causing duplicate visit entries.

## Solution
Implemented **10-second deduplication window** that:

1. Checks if the same IP address visited the same link within the last 10 seconds
2. If yes, skips logging a new visit (treats it as duplicate/prefetch)
3. Still redirects the user properly to maintain functionality

### Code Logic
```python
# Check if this same IP visited within the last 10 seconds
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
    # (prefetch/preview request detected)
```

## Benefits

✅ **Accurate Click Counts** - No more double counting from app prefetches
✅ **Better Analytics** - Referrer graph now shows true unique visitors
✅ **Maintains Functionality** - Users still get redirected properly
✅ **Works for All Apps** - Handles WhatsApp, Facebook, Instagram, Twitter, etc.

## Time Window: Why 10 Seconds?

- **Too Short (< 5s)**: Might miss some prefetch requests
- **Too Long (> 30s)**: Might incorrectly block legitimate repeat visits
- **10 seconds**: Sweet spot that catches prefetch while allowing real revisits

## Testing

To test this fix:
1. Share a link in WhatsApp
2. Click the link from WhatsApp
3. Check analytics - should show **1 click**, not 2
4. Wait 15+ seconds and click again - should show **2 clicks** (legitimate)

## Impact on Existing Data

This fix only affects **new visits** going forward. Historical duplicate visits remain in the database but won't affect future tracking.

## Related Files Modified
- `routes/links.py` - Added deduplication logic in `redirect_link()` function
