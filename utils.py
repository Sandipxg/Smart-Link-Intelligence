"""
Smart Link Intelligence - Utility Functions
Geolocation, device detection, email, and other utility functions
"""

import hashlib
import os
import re
import string
import uuid
import smtplib
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter
from email.message import EmailMessage
from flask import request, session
from database import query_db, execute_db
from config import SUSPICIOUS_INTERVAL_SECONDS, MULTI_CLICK_THRESHOLD, RETURNING_WINDOW_HOURS


def utcnow() -> datetime:
    """Get current UTC datetime"""
    return datetime.utcnow()


def hash_value(value: str) -> str:
    """Hash a value using SHA256"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_code(length: int = 6) -> str:
    """Generate a random code"""
    alphabet = string.ascii_letters + string.digits
    return "".join(alphabet[int.from_bytes(os.urandom(2), "big") % len(alphabet)] for _ in range(length))


def ensure_session() -> str:
    """Ensure session ID exists and return it"""
    sess_id = session.get("sid")
    if sess_id:
        return sess_id
    sess_id = str(uuid.uuid4())
    session["sid"] = sess_id
    return sess_id


def get_link_password_hash(link):
    """Safely get password hash from link row object"""
    try:
        return link["password_hash"] if link["password_hash"] else None
    except (KeyError, IndexError, TypeError):
        return None


def send_email(to_email, subject, html_content):
    """Send email using SMTP"""
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

    if not EMAIL_USER or not EMAIL_PASS:
        print("--- MOCK EMAIL SENDING (Missing Credentials) ---")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Content: {html_content[:100]}...")  # Truncate for log
        print("------------------------------------------------")
        return

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.set_content("This email requires HTML support.")
    msg.add_alternative(html_content, subtype="html")

    try:
        # TLS is preferred (secure + widely allowed)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed – check App Password")
        return False
    except Exception as e:
        print("❌ Email error:", e)
        return False


def classify_behavior(link_id: int, session_id: str, visits, now: datetime, behavior_rule=None) -> str:
    """Classify user behavior based on custom or default rules"""
    
    # Get behavior rule settings safely
    if behavior_rule:
        # Use .get() to avoid KeyError if the dict is missing these specific keys
        returning_window_hours = behavior_rule.get("returning_window_hours", RETURNING_WINDOW_HOURS)
        interested_threshold = behavior_rule.get("interested_threshold", 2)
        engaged_threshold = behavior_rule.get("engaged_threshold", MULTI_CLICK_THRESHOLD)
    else:
        # Use default values if no rule provided
        returning_window_hours = RETURNING_WINDOW_HOURS
        interested_threshold = 2
        engaged_threshold = MULTI_CLICK_THRESHOLD
    
    # Count recent visits within the custom window
    recent = [datetime.fromisoformat(v["ts"]) for v in visits if (now - datetime.fromisoformat(v["ts"])) < timedelta(hours=returning_window_hours)]
    
    # Count total visits for this session
    res = query_db(
        """
        SELECT COUNT(*) AS c FROM visits
        WHERE link_id = ? AND session_id = ?
        """,
        [link_id, session_id],
        one=True,
    )
    per_session = res["c"] if res else 0

    # Apply custom thresholds
    if per_session >= engaged_threshold:
        return "Highly engaged", per_session
    if len(recent) >= interested_threshold:
        return "Interested", per_session
    return "Curious", per_session


def detect_suspicious(visits, now: datetime, ip_hash: str = None, rules: dict = None) -> bool:
    """
    Detect suspicious activity based on bot-like patterns.
    
    This function now looks for:
    1. Extremely rapid requests from the SAME IP (< Customizable)
    2. Repeated identical patterns (bot signatures)
    
    It does NOT flag legitimate high traffic as suspicious.
    Load testing and legitimate high-frequency traffic is allowed.
    """
    if not rules:
        rules = {'rapid_click_limit': 0.3}
        
    from flask import request
    
    # Check for load testing headers - allow legitimate load tests
    if request and hasattr(request, 'headers'):
        # Check for common load testing indicators
        user_agent = request.headers.get("User-Agent", "").lower()
        x_load_test = request.headers.get("X-Load-Test", "").lower()
        
        # Allow if explicitly marked as load test
        if x_load_test == "true":
            return False
            
        # Allow common load testing tools
        load_test_agents = [
            "jmeter", "apache-httpclient", "loadrunner", "gatling", 
            "artillery", "k6", "wrk", "siege", "ab/", "curl/",
            "python-requests", "go-http-client"
        ]
        
        if any(agent in user_agent for agent in load_test_agents):
            print(f"DEBUG: Whitelisted agent found in detect_suspicious: {user_agent}")
            return False
            
    if len(visits) < 3:
        return False
    
    # If we have the current IP hash, check for rapid requests from THIS specific IP
    if ip_hash:
        # Get recent visits from this specific IP
        same_ip_visits = [v for v in visits if v['ip_hash'] == ip_hash]
        
        if len(same_ip_visits) >= 2:
            # Check if this IP is making requests faster than humanly possible
            latest = datetime.fromisoformat(same_ip_visits[0]["ts"])
            second_latest = datetime.fromisoformat(same_ip_visits[1]["ts"])
            delta = (latest - second_latest).total_seconds()
            
            # Flag as suspicious if same IP makes requests < rapid_click_limit
            rapid_limit = rules.get('rapid_click_limit', 0.3)
            if delta < rapid_limit:
                return True
    
    # Check for burst pattern: 8+ requests in 1 second (clear bot signature)
    # Increased threshold from 5 to 8 and reduced time from 2s to 1s
    # This catches obvious bots but allows legitimate rapid clicking
    recent_timestamps = [datetime.fromisoformat(v["ts"]) for v in visits[:15]]
    if len(recent_timestamps) >= 8:
        time_span = (recent_timestamps[0] - recent_timestamps[7]).total_seconds()
        if time_span < 1.0:
            return True
    
    return False


def decide_target(link, behavior: str, session_count: int) -> str:
    """Decide target URL based on behavior and rules"""
    # Use dictionary syntax for sqlite3.Row
    rule = (link["behavior_rule"] if link["behavior_rule"] else "standard").lower()
    
    if rule == "progression":
        if session_count <= 1:
            return link["primary_url"]
        if session_count == 2:
            return link["returning_url"]
        return link["cta_url"]

    # standard behavior-based routing
    if behavior == "Highly engaged":
        return link["cta_url"]
    if behavior == "Interested":
        return link["returning_url"]
    return link["primary_url"]


def evaluate_state(link_id: int, now: datetime, rules: dict = None) -> str:
    """Evaluate link state based on activity"""
    if not rules:
        rules = {'health_kill_switch': 5}
        
    from config import STATE_DECAY_DAYS, ATTENTION_DECAY_DAYS
    
    recent = query_db(
        """
        SELECT ts, is_suspicious FROM visits
        WHERE link_id = ?
        ORDER BY ts DESC
        LIMIT 30
        """,
        [link_id],
    )
    if not recent:
        return "Active"

    latest_time = datetime.fromisoformat(recent[0]["ts"])
    days_since = (now - latest_time).days
    suspicious_hits = sum(1 for v in recent if v["is_suspicious"])

    kill_threshold = rules.get('health_kill_switch', 5)
    if suspicious_hits >= kill_threshold:
        return "Inactive"
    if days_since > STATE_DECAY_DAYS:
        return "Inactive"
    if days_since > ATTENTION_DECAY_DAYS:
        return "Decaying"
    if len(recent) >= 10:
        return "High Interest"
    return "Active"


def trust_score(link_id: int) -> int:
    """Calculate trust score for a link"""
    metrics = query_db(
        """
        SELECT
            COUNT(*) AS total,
            SUM(is_suspicious) AS suspicious,
            SUM(CASE WHEN behavior = 'Highly engaged' THEN 1 ELSE 0 END) AS engaged
        FROM visits WHERE link_id = ?
        """,
        [link_id],
        one=True,
    )
    total = metrics["total"] or 0
    suspicious = metrics["suspicious"] or 0
    engaged = metrics["engaged"] or 0
    if total == 0:
        return 50
    score = 70 + int((engaged / max(total, 1)) * 20) - int((suspicious / max(total, 1)) * 40)
    return max(1, min(score, 100))


def attention_decay(visits):
    """Calculate attention decay over time"""
    if not visits:
        return []
    # bucket by day to show drop-off
    buckets = {}
    for v in visits:
        day = datetime.fromisoformat(v["ts"]).date().isoformat()
        buckets[day] = buckets.get(day, 0) + 1
    return [{"day": k, "count": buckets[k]} for k in sorted(buckets.keys())]


def detect_device(user_agent: str) -> str:
    """Detect device type from user agent string"""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "Mobile"
    elif "tablet" in ua or "ipad" in ua:
        return "Tablet"
    else:
        return "Desktop"


# Simple in-memory cache for geolocation (IP -> dict)
# In production, use Redis or database
geo_cache = {}


def get_client_ip():
    """Get the best available client IP address, checking proxy headers"""
    # Check X-Forwarded-For (standard for proxies)
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    
    # Check X-Real-IP (common alternative)
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
        
    # Fallback to direct connection
    return request.remote_addr or "unknown"


def get_public_ip_fallback():
    """Fetch the server's own public IP"""
    try:
        response = requests.get('https://api.ipify.org', timeout=3)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"Could not fetch public IP: {e}")
    return None


def get_api_location(ip: str) -> dict:
    """Get location data from ip-api.com with caching"""
    
    # Handle private IPs by trying to resolve public IP (for dev/testing)
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10."):
        print(f"Private IP detected ({ip}). Attempting to fetch public IP for geolocation...", flush=True)
        public_ip = get_public_ip_fallback()
        if public_ip:
            print(f"Using public IP {public_ip} instead of {ip}", flush=True)
            ip = public_ip
        else:
            return {'status': 'private'}
    
    # Check cache
    if ip in geo_cache:
        return geo_cache[ip]
    
    # Priority 1: IP2Location.io
    try:
        api_key = os.environ.get("IP2LOCATION_API_KEY", "E7A157580629094000305F862A145025")
        url = f"https://api.ip2location.io/?key={api_key}&ip={ip}&format=json"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            if 'country_name' in data:
                mapped_data = {
                    'status': 'success',
                    'country': data.get('country_name'),
                    'countryCode': data.get('country_code'),
                    'regionName': data.get('region_name'),
                    'city': data.get('city_name'),
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'timezone': data.get('time_zone'),
                    'isp': data.get('isp'),
                    'org': data.get('as')
                }
                geo_cache[ip] = mapped_data
                return mapped_data
    except Exception as e:
        print(f"IP2Location error: {e}")
        print("Falling back to ip-api.com...")

    # Priority 2: ip-api.com (Fallback)
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                geo_cache[ip] = data
                return data
    except Exception as e:
        print(f"API Geolocation error for {ip}: {e}")
        
    return {'status': 'fail'}


def detect_region(ip: str) -> str:
    """Detect region from IP address"""
    data = get_api_location(ip)
    
    if data.get('status') == 'private':
        return "Local/Private"
        
    if data.get('status') == 'success':
        city = data.get('city', '')
        country = data.get('country', 'Unknown Country')
        if city:
            return f"{city}, {country}"
        return country
        
    return "Unknown"


def get_detailed_location(ip: str) -> dict:
    """Get detailed location information including country, city, coordinates"""
    location_info = {
        'country': 'Unknown',
        'city': 'Unknown', 
        'region': 'Unknown',
        'latitude': None,
        'longitude': None,
        'timezone': None
    }
    
    data = get_api_location(ip)
    
    if data.get('status') == 'private':
        location_info['country'] = 'Local/Private'
        location_info['region'] = 'Local/Private'
        return location_info
        
    if data.get('status') == 'success':
        location_info['country'] = data.get('country', 'Unknown')
        location_info['city'] = data.get('city', 'Unknown')
        location_info['region'] = data.get('regionName', 'Unknown')
        location_info['latitude'] = data.get('lat')
        location_info['longitude'] = data.get('lon')
        location_info['timezone'] = data.get('timezone')
    
    return location_info


def country_to_continent(country: str) -> str:
    """Map country names to continents"""
    if not country or country in ['Unknown', 'Local/Private']:
        return country
    
    # Comprehensive country to continent mapping
    continent_map = {
        # Asia
        'India': 'Asia',
        'China': 'Asia',
        'Japan': 'Asia',
        'South Korea': 'Asia',
        'Thailand': 'Asia',
        'Vietnam': 'Asia',
        'Singapore': 'Asia',
        'Malaysia': 'Asia',
        'Indonesia': 'Asia',
        'Philippines': 'Asia',
        'Bangladesh': 'Asia',
        'Pakistan': 'Asia',
        'Sri Lanka': 'Asia',
        'Nepal': 'Asia',
        'Myanmar': 'Asia',
        'Cambodia': 'Asia',
        'Laos': 'Asia',
        'Mongolia': 'Asia',
        'Kazakhstan': 'Asia',
        'Uzbekistan': 'Asia',
        'Kyrgyzstan': 'Asia',
        'Tajikistan': 'Asia',
        'Turkmenistan': 'Asia',
        'Afghanistan': 'Asia',
        'Iran': 'Asia',
        'Iraq': 'Asia',
        'Saudi Arabia': 'Asia',
        'United Arab Emirates': 'Asia',
        'Qatar': 'Asia',
        'Kuwait': 'Asia',
        'Bahrain': 'Asia',
        'Oman': 'Asia',
        'Yemen': 'Asia',
        'Jordan': 'Asia',
        'Lebanon': 'Asia',
        'Syria': 'Asia',
        'Israel': 'Asia',
        'Palestine': 'Asia',
        'Turkey': 'Asia',
        'Cyprus': 'Asia',
        'Georgia': 'Asia',
        'Armenia': 'Asia',
        'Azerbaijan': 'Asia',
        'Russia': 'Asia',
        'Taiwan': 'Asia',
        'Hong Kong': 'Asia',
        'Macau': 'Asia',
        'North Korea': 'Asia',
        'Brunei': 'Asia',
        'Maldives': 'Asia',
        'Bhutan': 'Asia',
        'Timor-Leste': 'Asia',
        
        # North America
        'United States': 'North America',
        'Canada': 'North America',
        'Mexico': 'North America',
        'Guatemala': 'North America',
        'Belize': 'North America',
        'El Salvador': 'North America',
        'Honduras': 'North America',
        'Nicaragua': 'North America',
        'Costa Rica': 'North America',
        'Panama': 'North America',
        'Cuba': 'North America',
        'Jamaica': 'North America',
        'Haiti': 'North America',
        'Dominican Republic': 'North America',
        'Bahamas': 'North America',
        'Barbados': 'North America',
        'Trinidad and Tobago': 'North America',
        'Grenada': 'North America',
        'Saint Lucia': 'North America',
        'Saint Vincent and the Grenadines': 'North America',
        'Antigua and Barbuda': 'North America',
        'Dominica': 'North America',
        'Saint Kitts and Nevis': 'North America',
        
        # Europe
        'United Kingdom': 'Europe',
        'Germany': 'Europe',
        'France': 'Europe',
        'Italy': 'Europe',
        'Spain': 'Europe',
        'Netherlands': 'Europe',
        'Belgium': 'Europe',
        'Switzerland': 'Europe',
        'Austria': 'Europe',
        'Sweden': 'Europe',
        'Norway': 'Europe',
        'Denmark': 'Europe',
        'Finland': 'Europe',
        'Iceland': 'Europe',
        'Ireland': 'Europe',
        'Portugal': 'Europe',
        'Poland': 'Europe',
        'Czech Republic': 'Europe',
        'Slovakia': 'Europe',
        'Hungary': 'Europe',
        'Romania': 'Europe',
        'Bulgaria': 'Europe',
        'Greece': 'Europe',
        'Croatia': 'Europe',
        'Slovenia': 'Europe',
        'Serbia': 'Europe',
        'Bosnia and Herzegovina': 'Europe',
        'Montenegro': 'Europe',
        'North Macedonia': 'Europe',
        'Albania': 'Europe',
        'Kosovo': 'Europe',
        'Estonia': 'Europe',
        'Latvia': 'Europe',
        'Lithuania': 'Europe',
        'Belarus': 'Europe',
        'Ukraine': 'Europe',
        'Moldova': 'Europe',
        'Luxembourg': 'Europe',
        'Monaco': 'Europe',
        'Liechtenstein': 'Europe',
        'San Marino': 'Europe',
        'Vatican City': 'Europe',
        'Malta': 'Europe',
        'Andorra': 'Europe',
        
        # South America
        'Brazil': 'South America',
        'Argentina': 'South America',
        'Chile': 'South America',
        'Peru': 'South America',
        'Colombia': 'South America',
        'Venezuela': 'South America',
        'Ecuador': 'South America',
        'Bolivia': 'South America',
        'Paraguay': 'South America',
        'Uruguay': 'South America',
        'Guyana': 'South America',
        'Suriname': 'South America',
        'French Guiana': 'South America',
        
        # Africa
        'Nigeria': 'Africa',
        'South Africa': 'Africa',
        'Egypt': 'Africa',
        'Kenya': 'Africa',
        'Ghana': 'Africa',
        'Morocco': 'Africa',
        'Algeria': 'Africa',
        'Tunisia': 'Africa',
        'Libya': 'Africa',
        'Sudan': 'Africa',
        'Ethiopia': 'Africa',
        'Uganda': 'Africa',
        'Tanzania': 'Africa',
        'Zimbabwe': 'Africa',
        'Zambia': 'Africa',
        'Botswana': 'Africa',
        'Namibia': 'Africa',
        'Angola': 'Africa',
        'Mozambique': 'Africa',
        'Madagascar': 'Africa',
        'Mauritius': 'Africa',
        'Seychelles': 'Africa',
        'Cameroon': 'Africa',
        'Ivory Coast': 'Africa',
        'Senegal': 'Africa',
        'Mali': 'Africa',
        'Burkina Faso': 'Africa',
        'Niger': 'Africa',
        'Chad': 'Africa',
        'Central African Republic': 'Africa',
        'Democratic Republic of the Congo': 'Africa',
        'Republic of the Congo': 'Africa',
        'Gabon': 'Africa',
        'Equatorial Guinea': 'Africa',
        'Rwanda': 'Africa',
        'Burundi': 'Africa',
        'Djibouti': 'Africa',
        'Somalia': 'Africa',
        'Eritrea': 'Africa',
        'Malawi': 'Africa',
        'Lesotho': 'Africa',
        'Swaziland': 'Africa',
        'Gambia': 'Africa',
        'Guinea-Bissau': 'Africa',
        'Guinea': 'Africa',
        'Sierra Leone': 'Africa',
        'Liberia': 'Africa',
        'Togo': 'Africa',
        'Benin': 'Africa',
        'Mauritania': 'Africa',
        'Cape Verde': 'Africa',
        'Comoros': 'Africa',
        'São Tomé and Príncipe': 'Africa',
        
        # Oceania
        'Australia': 'Oceania',
        'New Zealand': 'Oceania',
        'Papua New Guinea': 'Oceania',
        'Fiji': 'Oceania',
        'Solomon Islands': 'Oceania',
        'Vanuatu': 'Oceania',
        'Samoa': 'Oceania',
        'Tonga': 'Oceania',
        'Kiribati': 'Oceania',
        'Tuvalu': 'Oceania',
        'Nauru': 'Oceania',
        'Palau': 'Oceania',
        'Marshall Islands': 'Oceania',
        'Micronesia': 'Oceania',
        
        # Antarctica
        'Antarctica': 'Antarctica',
    }
    
    # Return mapped continent or the original country if not found
    return continent_map.get(country, country)


def parse_browser(user_agent: str) -> str:
    """Parse browser name and version from User-Agent string"""
    if not user_agent or user_agent == "unknown":
        return "Unknown"
    
    ua = user_agent.lower()
    
    # Check for common browsers (order matters - more specific first)
    if "edg/" in ua or "edge/" in ua:
        import re
        match = re.search(r'edg[e]?/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Microsoft Edge ({version})" if version else "Microsoft Edge"
    
    if "opr/" in ua or "opera" in ua:
        import re
        match = re.search(r'(?:opr|opera)[/\s](\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Opera ({version})" if version else "Opera"
    
    if "chrome" in ua and "chromium" not in ua:
        import re
        match = re.search(r'chrome/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Chrome ({version})" if version else "Chrome"
    
    if "firefox" in ua:
        import re
        match = re.search(r'firefox/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Firefox ({version})" if version else "Firefox"
    
    if "safari" in ua and "chrome" not in ua:
        import re
        match = re.search(r'version/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Safari ({version})" if version else "Safari"
    
    if "msie" in ua or "trident" in ua:
        import re
        match = re.search(r'(?:msie |rv:)(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Internet Explorer ({version})" if version else "Internet Explorer"
    
    if "chromium" in ua:
        return "Chromium"
    
    return "Unknown Browser"


def parse_os(user_agent: str) -> str:
    """Parse operating system from User-Agent string"""
    if not user_agent or user_agent == "unknown":
        return "Unknown"
    
    ua = user_agent.lower()
    
    # Windows versions
    if "windows nt 10.0" in ua:
        if "windows nt 10.0; win64" in ua:
            return "Windows 10/11 x64"
        return "Windows 10/11"
    if "windows nt 6.3" in ua:
        return "Windows 8.1"
    if "windows nt 6.2" in ua:
        return "Windows 8"
    if "windows nt 6.1" in ua:
        return "Windows 7"
    if "windows nt 6.0" in ua:
        return "Windows Vista"
    if "windows nt 5.1" in ua or "windows xp" in ua:
        return "Windows XP"
    if "windows" in ua:
        return "Windows"
    
    # macOS
    if "mac os x" in ua:
        import re
        match = re.search(r'mac os x (\d+[_\.]\d+)', ua)
        if match:
            version = match.group(1).replace('_', '.')
            return f"macOS {version}"
        return "macOS"
    
    # iOS
    if "iphone" in ua:
        import re
        match = re.search(r'iphone os (\d+[_\.]\d+)', ua)
        if match:
            version = match.group(1).replace('_', '.')
            return f"iOS {version} (iPhone)"
        return "iOS (iPhone)"
    if "ipad" in ua:
        return "iOS (iPad)"
    
    # Android
    if "android" in ua:
        import re
        match = re.search(r'android (\d+[\.\d]*)', ua)
        if match:
            return f"Android {match.group(1)}"
        return "Android"
    
    # Linux distributions
    if "ubuntu" in ua:
        return "Ubuntu Linux"
    if "fedora" in ua:
        return "Fedora Linux"
    if "linux" in ua:
        return "Linux"
    
    # Chrome OS
    if "cros" in ua:
        return "Chrome OS"
    
    return "Unknown OS"


def normalize_isp(isp_name: str) -> str:
    """Normalize common ISP names to prevent duplicates in analytics"""
    if not isp_name or isp_name.lower() == 'unknown':
        return "Other/Unknown"
    
    name = isp_name.strip()
    # Remove trailing dot if exists
    if name.endswith('.'):
        name = name[:-1].strip()
        
    name_lower = name.lower()
    
    # Reliance Jio variations
    if "reliance jio" in name_lower or "reliancejio" in name_lower:
        return "Reliance Jio"
    
    # Airtel variations
    if "bharti airtel" in name_lower or "airtel" in name_lower:
        return "Bharti Airtel"
    
    # Vodafone Idea variations
    if "vodafone" in name_lower or "idea" in name_lower:
        return "Vi (Vodafone Idea)"
    
    # BSNL variations
    if "bsnl" in name_lower or "bharat sanchar" in name_lower:
        return "BSNL"
    
    # Tata Tele/Communications
    if "tata tele" in name_lower or "tata comm" in name_lower:
        return "Tata"
        
    return name


def get_isp_info(ip: str) -> dict:
    """Get ISP and hostname via DNS reverse lookup and API fallback"""
    result = {
        'isp': 'Unknown',
        'hostname': 'Unknown',
        'org': 'Unknown'
    }
    
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10."):
        # Try to get public IP for dev mode to show real ISP
        public_ip = get_public_ip_fallback()
        if public_ip:
            ip = public_ip
        else:
            result['isp'] = 'Local Network'
            result['hostname'] = 'localhost'
            return result
    
    # Try DNS reverse lookup for hostname
    try:
        import socket
        hostname = socket.gethostbyaddr(ip)[0]
        result['hostname'] = hostname
        
        # Extract potential ISP from hostname
        parts = hostname.split('.')
        if len(parts) >= 2:
            result['isp'] = '.'.join(parts[-2:])
    except (socket.herror, socket.gaierror, socket.timeout):
        pass
    
    # Try ip-api.com for accurate ISP info
    try:
        import requests
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=isp,org,as", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('isp'):
                result['isp'] = normalize_isp(data['isp'])
            if data.get('org'):
                result['org'] = data['org']
    except Exception:
        pass
    
    return result