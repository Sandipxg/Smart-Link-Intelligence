import sqlite3

# Connect to database
conn = sqlite3.connect('smart_links.db')
cursor = conn.cursor()

# Check referrer data
print("=" * 60)
print("CHECKING SOCIAL REFERRERS FEATURE")
print("=" * 60)

# 1. Check if referrer column has data
cursor.execute("SELECT COUNT(*) FROM visits WHERE referrer IS NOT NULL AND referrer != 'no referrer'")
referrer_count = cursor.fetchone()[0]
print(f"\n1. Total visits with referrer data: {referrer_count}")

# 2. Show sample referrers
cursor.execute("SELECT referrer, COUNT(*) as count FROM visits WHERE referrer IS NOT NULL AND referrer != 'no referrer' GROUP BY referrer LIMIT 10")
referrers = cursor.fetchall()
print("\n2. Sample referrer data:")
if referrers:
    for ref, count in referrers:
        display_ref = ref[:60] + "..." if len(ref) > 60 else ref
        print(f"   {display_ref} : {count} clicks")
else:
    print("   No referrer data found")

# 3. Check for social media referrers
social_platforms = ['facebook', 'twitter', 't.co', 'instagram', 'linkedin', 'youtube']
social_found = []
cursor.execute("SELECT referrer FROM visits WHERE referrer IS NOT NULL AND referrer != 'no referrer'")
all_referrers = cursor.fetchall()
for ref_tuple in all_referrers:
    ref = ref_tuple[0].lower()
    for platform in social_platforms:
        if platform in ref:
            social_found.append((ref_tuple[0], platform))
            break

print(f"\n3. Social media referrers found: {len(social_found)}")
if social_found:
    for ref, platform in social_found[:5]:
        print(f"   Platform: {platform} - URL: {ref[:50]}...")

# 4. Test the aggregation logic
social_platforms_full = {
    'facebook': 'Facebook',
    'messenger': 'Facebook',
    'instagram': 'Instagram',
    'twitter': 'Twitter',
    't.co': 'Twitter',
    'x.com': 'Twitter',
    'linkedin': 'LinkedIn',
    'pinterest': 'Pinterest',
    'reddit': 'Reddit',
    'youtube': 'YouTube',
    'youtu.be': 'YouTube',
    'tiktok': 'TikTok',
    'whatsapp': 'WhatsApp',
}

social_counts = {}
cursor.execute("SELECT referrer, COUNT(*) as count FROM visits WHERE referrer IS NOT NULL AND referrer != 'no referrer' GROUP BY referrer")
for row in cursor.fetchall():
    ref = row[0].lower()
    for key, name in social_platforms_full.items():
        if key in ref:
            social_counts[name] = social_counts.get(name, 0) + row[1]
            break

print("\n4. Aggregated social referrers (as shown in analytics):")
if social_counts:
    for network, count in sorted(social_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {network}: {count} clicks")
else:
    print("   No social media clicks detected yet")

print("\n" + "=" * 60)
print("FEATURE STATUS:")
if social_counts:
    print("✓ Social Referrers Feature is WORKING")
    print(f"  Found {len(social_counts)} social platforms with traffic")
else:
    print("⚠ Social Referrers Feature is ready but NO DATA YET")
    print("  To test: Share your link on social media and click it")
print("=" * 60)

conn.close()
