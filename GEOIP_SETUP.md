# MaxMind GeoIP Setup Guide

Your Smart Link Intelligence application now uses MaxMind GeoIP for accurate location tracking in analytics.

## Automatic Setup (Recommended)

The application will automatically download a free GeoLite2 database when you first run it. No additional setup required!

## Manual Setup (Optional)

If you want to use your own MaxMind license key for more accurate data:

### 1. Get a MaxMind License Key

1. Sign up for a free account at https://www.maxmind.com/en/geolite2/signup
2. Log in to your MaxMind account
3. Go to "My License Key" in the left sidebar
4. Generate a new license key
5. Copy your license key

### 2. Configure Your License Key

Edit the `GEOIP_DB_URL` in `app.py` and replace `YOUR_LICENSE_KEY` with your actual license key:

```python
GEOIP_DB_URL = "https://download.maxmind.com/app/geoip_update?edition_id=GeoLite2-City&license_key=YOUR_ACTUAL_LICENSE_KEY&suffix=tar.gz"
```

### 3. Delete Existing Database (if any)

If you already have a `GeoLite2-City.mmdb` file, delete it so the application downloads a fresh copy with your license key.

## Features

With MaxMind GeoIP integration, your analytics now include:

- **Accurate Country Detection**: Real country names instead of simulated regions
- **City-Level Tracking**: See which cities your visitors are from
- **Detailed Location Data**: Country, city, region, and coordinates
- **Enhanced Analytics**: New "Top Cities" chart in analytics
- **Better CSV Exports**: More detailed location data in exports

## Privacy & Compliance

- IP addresses are hashed and not stored in plain text
- Only aggregated location statistics are displayed
- No personal information is collected or stored
- Complies with privacy regulations

## Troubleshooting

If location detection isn't working:

1. Check that `GeoLite2-City.mmdb` exists in your project directory
2. Ensure you have internet access for the initial database download
3. Check the console for any error messages
4. The application will fall back to basic region detection if GeoIP fails

## Database Updates

The GeoLite2 database should be updated regularly (monthly) for best accuracy. You can:

1. Delete the existing `GeoLite2-City.mmdb` file
2. Restart the application to download a fresh copy

Or set up automatic updates using MaxMind's geoipupdate tool.