# JMeter Load Test Configuration for Smart Link Intelligence

## Problem Fixed
The DDoS protection was too aggressive and blocking legitimate load testing traffic. The system has been updated to:

1. **Increased Thresholds**: 
   - Suspicious threshold: 10 → 25
   - DDoS threshold: 50 → 100
   - Rate limits: 60/min → 120/min per IP
   - Burst threshold: 100 → 200 requests in 10 seconds

2. **Load Test Detection**: 
   - Detects JMeter and other load testing tools by User-Agent
   - Supports `X-Load-Test: true` header for explicit bypass
   - Less aggressive suspicious activity detection

## JMeter Configuration

### Option 1: Add Load Test Header (Recommended)
1. In your JMeter test plan, right-click on your Thread Group
2. Add → Config Element → HTTP Header Manager
3. Add header:
   - **Name**: `X-Load-Test`
   - **Value**: `true`

### Option 2: JMeter is Auto-Detected
JMeter requests are automatically detected by User-Agent and allowed through. No additional configuration needed.

## Updated Detection Logic

### Suspicious Activity Detection
- **Before**: 5+ requests in 2 seconds = suspicious
- **After**: 8+ requests in 1 second = suspicious
- **Before**: Same IP < 0.5 seconds apart = suspicious  
- **After**: Same IP < 0.3 seconds apart = suspicious

### Load Test Bypass
The system now allows these User-Agents without DDoS protection:
- `jmeter`
- `apache-httpclient`
- `loadrunner`
- `gatling`
- `artillery`
- `k6`
- `wrk`
- `siege`
- `curl`
- `python-requests`

## Test Your Configuration

1. **Run your JMeter test** with 20 threads, 3-second ramp-up
2. **Monitor the link** - it should no longer be blocked
3. **Check analytics** - visits should show as legitimate (not suspicious)

## Verification Commands

```bash
# Test with curl and load test header
curl -H "X-Load-Test: true" https://smartlinkintelligence.pythonanywhere.com/r/YOUR_LINK_CODE

# Test with JMeter User-Agent
curl -H "User-Agent: Apache-HttpClient/4.5.13 (Java/11.0.16)" https://smartlinkintelligence.pythonanywhere.com/r/YOUR_LINK_CODE
```

## What Changed in the Code

1. **utils.py**: `detect_suspicious()` function now:
   - Checks for load testing User-Agents and headers
   - Uses more lenient thresholds (8 requests in 1 second vs 5 in 2 seconds)
   - Reduced same-IP detection from 0.5s to 0.3s

2. **ddos_protection.py**: `DDoSProtection` class now:
   - Increased all rate limiting thresholds
   - Added load test bypass in `check_rate_limit()`
   - Added load test bypass in `detect_ddos_attack()`

The system now distinguishes between:
- **Real DDoS attacks**: Malicious bot traffic with suspicious patterns
- **Load testing**: Legitimate high-frequency testing with recognizable tools
- **High legitimate traffic**: Real users during peak usage

Your JMeter tests should now work without triggering false DDoS protection!