# Smart Link Intelligence - Admin Panel

## Overview

The Smart Link Intelligence Admin Panel provides comprehensive administrative control over the platform with advanced user management, ad management, revenue analytics, and activity monitoring capabilities.

## Features

### 🔐 Security
- **Password Protection**: Admin password required every time (no session persistence)
- **Separate Authentication**: Independent from regular user accounts
- **Activity Logging**: All admin actions are logged with timestamps and IP addresses

### 👥 User Management
- **Complete CRUD Operations**: Create, view, edit, and delete users
- **Premium Management**: Grant/revoke premium status for any user
- **Membership Tiers**: Manage Free, Elite, and Elite Pro memberships
- **User Analytics**: View individual user statistics and revenue generation
- **Bulk Operations**: Export user data to CSV

### 📊 Advanced Analytics
- **Revenue Tracking**: Real-time ad impression revenue tracking
  - Large ads: $0.05 per impression
  - Small ads: $0.02 per impression
- **Performance Metrics**: Daily revenue trends, top performers
- **Growth Analytics**: User registration and link creation trends
- **Export Functionality**: CSV exports for all data

### 🎯 Ad Management
- **Create Ads for Any User**: Override Elite Pro restrictions
- **Random Ad Selection**: 1 large + 2 small ads per page
- **Revenue Automation**: Automatic impression tracking and revenue calculation
- **Ad Performance**: Track impressions and revenue by ad type
- **Bulk Ad Operations**: Toggle active status, delete ads

### 📈 Activity Monitoring
- **Real-time Activity Feed**: Monitor all user actions
- **Detailed Logging**: Login, link creation, analytics views, upgrades
- **IP Tracking**: Monitor user locations and suspicious activity
- **Filtering**: Search by user, activity type, date range
- **Auto-refresh**: Optional real-time updates

## Access Information

### Default Credentials
- **URL**: `http://localhost:5000/admin/login`
- **Password**: `admin123` (Change in production!)

### Navigation
- Access via user dropdown menu → "Admin Panel"
- Direct URL: `/admin/login`

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
The admin tables are automatically created when the application starts.

### 3. Create Sample Data (Optional)
```bash
python test_admin.py
```

### 4. Start Application
```bash
python app.py
```

## Admin Panel Structure

### Dashboard (`/admin/`)
- Overview statistics (users, revenue, links, ads)
- Top performing links
- Recent admin activities
- Premium user overview

### User Management (`/admin/users`)
- Paginated user list with search
- User details with links, ads, and activity
- Premium status management
- User deletion with cascade cleanup
- CSV export functionality

### Ad Management (`/admin/ads`)
- Visual ad gallery with previews
- Ad statistics (impressions, revenue)
- Toggle active status
- Delete ads
- Revenue information display

### Revenue Analytics (`/admin/analytics`)
- Time-based revenue charts
- Ad performance breakdown
- Top revenue generating users
- Growth metrics
- Daily revenue breakdown
- Export revenue data

### Activity Monitoring (`/admin/activity`)
- Real-time activity feed
- Filter by user and activity type
- IP address tracking
- Activity statistics
- Auto-refresh capability

## Revenue System

### Ad Impression Rates
- **Large Ads (Position 1)**: $0.05 per impression
- **Small Ads (Positions 2-3)**: $0.02 per impression

### Revenue Tracking
- Automatic impression tracking when ads are displayed
- Real-time revenue calculation
- User-specific revenue attribution
- Daily/monthly revenue reports

### Ad Selection Algorithm
1. Random selection from active ads
2. 1 large ad + 2 small ads per page
3. Only link owner's ads are shown (privacy protection)
4. Position-based revenue calculation

## Security Features

### Password Protection
- Admin password required every session
- No "remember me" functionality
- Session expires on browser close

### Activity Logging
- All admin actions logged
- IP address tracking
- Timestamp recording
- Action details and targets

### Data Protection
- User privacy maintained (only link owner's ads shown)
- Secure password hashing
- SQL injection protection
- XSS prevention

## API Endpoints

### Admin Authentication
- `GET/POST /admin/login` - Admin login
- `GET /admin/logout` - Admin logout

### User Management
- `GET /admin/users` - User list with search/pagination
- `GET /admin/users/<id>` - User details
- `POST /admin/users/<id>/delete` - Delete user
- `POST /admin/users/<id>/toggle-premium` - Toggle premium status

### Ad Management
- `GET /admin/ads` - Ad management interface
- `GET/POST /admin/ads/create-for-user/<id>` - Create ad for user
- `POST /admin/ads/<id>/toggle` - Toggle ad status
- `POST /admin/ads/<id>/delete` - Delete ad

### Analytics & Export
- `GET /admin/analytics` - Revenue analytics dashboard
- `GET /admin/activity` - User activity monitoring
- `GET /admin/export/users` - Export users CSV
- `GET /admin/export/revenue` - Export revenue CSV

## Database Schema

### Admin Tables
```sql
-- Admin users
admin_users (id, username, password_hash, created_at, last_login, is_active)

-- Ad impressions tracking
ad_impressions (id, link_id, user_id, ad_type, ad_position, revenue, ip_address, timestamp)

-- Admin activity log
admin_activity_log (id, admin_id, action, target_type, target_id, details, timestamp, ip_address)

-- User activity tracking
user_activity (id, user_id, activity_type, details, ip_address, timestamp)
```

## Customization

### Change Admin Password
Edit `admin_panel.py`:
```python
ADMIN_PASSWORD_HASH = generate_password_hash("your_new_password")
```

### Modify Revenue Rates
Edit `admin_panel.py`:
```python
AD_REVENUE_RATES = {
    "large": 0.10,  # $0.10 per large ad
    "small": 0.05   # $0.05 per small ad
}
```

### Add Custom Activity Types
Extend the activity tracking in your routes:
```python
from admin_panel import log_admin_activity
log_admin_activity("custom_action", "target_type", target_id, "Details")
```

## Production Deployment

### Security Checklist
- [ ] Change default admin password
- [ ] Use environment variables for sensitive data
- [ ] Enable HTTPS
- [ ] Set up proper database backups
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerts

### Environment Variables
```bash
ADMIN_PASSWORD_HASH=your_secure_hash
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
```

## Troubleshooting

### Common Issues

1. **Admin login not working**
   - Check password hash in `admin_panel.py`
   - Verify database tables are created
   - Check browser console for errors

2. **Revenue not tracking**
   - Verify ad impressions table exists
   - Check `track_ad_impression` function calls
   - Review database permissions

3. **Export not working**
   - Check file permissions
   - Verify CSV module import
   - Review database query syntax

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the database schema
3. Examine the admin activity logs
4. Test with sample data using `test_admin.py`

## License

This admin panel is part of the Smart Link Intelligence platform and follows the same licensing terms as the main application.