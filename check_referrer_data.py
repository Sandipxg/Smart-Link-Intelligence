"""
Sanity check: Inspect raw referrer data in database
"""
import sqlite3

conn = sqlite3.connect('smart_links.db')
cursor = conn.cursor()

print("=" * 100)
print("RAW REFERRER DATA - Before Normalization")
print("=" * 100)

# Get all unique referrer values
cursor.execute("""
    SELECT 
        referrer,
        COUNT(DISTINCT ip_hash) as unique_visitors,
        COUNT(*) as total_visits
    FROM visits
    GROUP BY referrer
    ORDER BY unique_visitors DESC
""")

rows = cursor.fetchall()

if not rows:
    print("No visits found in database.")
else:
    print(f"\nFound {len(rows)} unique referrer values:\n")
    for ref, unique, total in rows:
        display_ref = f"'{ref}'" if ref else "(empty/NULL)"
        print(f"{display_ref:<50} | Unique: {unique:>3} | Total: {total:>3}")

print("\n" + "=" * 100)
print("NORMALIZED REFERRER DATA - After LOWER(TRIM())")
print("=" * 100)

# Simulate the normalized query
cursor.execute("""
    SELECT 
        LOWER(TRIM(referrer)) as normalized_ref,
        COUNT(DISTINCT ip_hash) as unique_visitors,
        COUNT(*) as total_visits
    FROM visits
    GROUP BY LOWER(TRIM(referrer))
    ORDER BY unique_visitors DESC
""")

norm_rows = cursor.fetchall()

print(f"\nAfter normalization: {len(norm_rows)} unique values:\n")
for ref, unique, total in norm_rows:
    display_ref = f"'{ref}'" if ref else "(empty/NULL)"
    print(f"{display_ref:<50} | Unique: {unique:>3} | Total: {total:>3}")

print("\n" + "=" * 100)
print("CLASSIFICATION PREVIEW")
print("=" * 100)

# Simulate the classification logic
classifications = {
    "Direct": 0,
    "Gmail": 0,
    "Google": 0,
    "Facebook": 0,
    "WhatsApp": 0,
    "Twitter": 0,
    "LinkedIn": 0,
    "YouTube": 0,
    "Other": 0
}

for ref, unique, total in norm_rows:
    if not ref or ref in ("no referrer", "none", "null", "-"):
        classifications["Direct"] += unique
    elif "whatsapp" in ref or ref in ("wa", "w"):
        classifications["WhatsApp"] += unique
    elif "gmail" in ref:
        classifications["Gmail"] += unique
    elif ref in ("google",):
        classifications["Google"] += unique
    elif "facebook" in ref or ref in ("fb", "fban", "fbav", "instagram"):
        classifications["Facebook"] += unique
    elif ref in ("twitter", "x") or "t.co" in ref:
        classifications["Twitter"] += unique
    elif "linkedin" in ref or "lnkd.in" in ref:
        classifications["LinkedIn"] += unique
    elif "youtube" in ref or "youtu.be" in ref:
        classifications["YouTube"] += unique
    else:
        # Try URL parsing
        from urllib.parse import urlparse
        try:
            if not ref.startswith(("http://", "https://")):
                test_ref = "http://" + ref
            else:
                test_ref = ref
            
            domain = urlparse(test_ref).netloc
            
            if "google." in domain:
                classifications["Google"] += unique
            elif "mail.google.com" in domain:
                classifications["Gmail"] += unique
            elif "facebook.com" in domain or "instagram.com" in domain:
                classifications["Facebook"] += unique
            elif "whatsapp.com" in domain or "wa.me" in domain:
                classifications["WhatsApp"] += unique
            elif "twitter.com" in domain or "x.com" in domain:
                classifications["Twitter"] += unique
            elif "linkedin.com" in domain:
                classifications["LinkedIn"] += unique
            elif "youtube.com" in domain or "youtu.be" in domain:
                classifications["YouTube"] += unique
            else:
                classifications["Other"] += unique
        except:
            classifications["Other"] += unique

print("\nExpected Chart Data (Unique Visitors):\n")
for platform, count in classifications.items():
    if count > 0:
        print(f"  {platform:<12} : {count:>3} unique visitors")

print("\n" + "=" * 100)
print("ISSUES TO FIX")
print("=" * 100)

# Check for common issues
issues = []

# Check for variations of "no referrer"
no_ref_variations = [r for r, _, _ in norm_rows if r and r in ("no referrer", "none", "null", "-")]
if no_ref_variations:
    issues.append(f"✓ Found {len(no_ref_variations)} 'no referrer' variations (will be merged into Direct)")

# Check for WhatsApp variations
wa_variations = [r for r, _, _ in norm_rows if r and ("whatsapp" in r or "wa.me" in r)]
if len(wa_variations) > 1:
    issues.append(f"✓ Found {len(wa_variations)} WhatsApp variations: {wa_variations} (will be merged)")

# Check for empty/null
empty_count = sum(unique for r, unique, _ in norm_rows if not r)
if empty_count > 0:
    issues.append(f"✓ Found {empty_count} visits with empty/NULL referrer (will be Direct)")

if issues:
    print("\nThe normalization will fix these issues:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("\n✅ No major data quality issues found!")

print("\n" + "=" * 100)

conn.close()
