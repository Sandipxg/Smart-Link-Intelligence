# 🚀 Smart Link Intelligence: Codebase Explanation 🧠

This document provides a detailed explanation of the non-UI code files within the "Smart Link Intelligence" project. Each section focuses on a specific file, outlining its purpose, key components, and its role in the overall application flow.

---

### 🐍 `app.py` - Main Application Entry Point

**🎯 Purpose:** This file serves as the main entry point for the Flask web application. It is responsible for creating and configuring the Flask application instance, setting up request handlers, initializing the database, and registering all the application's Blueprints (modular components).

**⚙️ Key Components & Functionality:**

*   **`create_app()` function:**
    *   Initializes the Flask application (`app = Flask(__name__)`).
    *   Loads configuration settings from `config.FLASK_CONFIG` into the app's configuration.
    *   Registers `_before_request` to run before each request and `close_db` (from `database.py`) to run when the application context tears down.
    *   Ensures the existence of an upload directory specified in the app configuration.
    *   Initializes both the main application database (`ensure_db()`) and admin-specific tables (`ensure_admin_tables()`).
    *   Initializes the `DDoSProtection` class, passing it the database path.
    *   Registers all the Flask Blueprints: `admin_bp`, `ddos_bp`, `main_bp`, `auth_bp`, `links_bp`, `user_bp`, and `ads_bp`. These Blueprints correspond to different functional areas of the application.
    *   Returns the configured Flask application instance.
*   **`_before_request()` function:**
    *   This function is executed before every request to the application.
    *   Calls `utils.ensure_session()` to ensure the user session is properly set up.
    *   Attempts to load the current logged-in user's information from the database based on the `USER_SESSION_KEY` stored in the session. The user object is then attached to `flask.g` for easy access throughout the request.
    *   **Maintenance Mode Check:** It checks a `system_settings` table in the database for a `maintenance_mode` flag.
        *   If maintenance mode is enabled, it exempts static files, admin routes (including `/admin/login`), and the maintenance page itself from redirection.
        *   If the user is not an admin and the request is not exempt, it clears the user's session and redirects them to the `main.maintenance` page. This ensures only authorized personnel can access the site during maintenance.
        *   Includes graceful error handling if the `system_settings` table doesn't exist or the query fails.
*   **Application Instance Creation (`app = create_app()`):**
    *   This line calls the `create_app()` function to instantiate and configure the Flask application.
*   **Development Server (`if __name__ == "__main__":`)**
    *   If the script is run directly, it starts the Flask development server with debugging enabled on `0.0.0.0:5000`.

**🔄 Role in Overall Application Flow:**

`app.py` is the central orchestrator. It brings together all the different modules (Blueprints), sets up the global application context, manages database initialization, and defines crucial pre-request logic like user session management and maintenance mode handling. It's the first file executed when the Flask application starts and ensures that all components are correctly configured and registered.

---

### 🛠️ `admin_panel.py` - Comprehensive Admin Panel and Management

**🎯 Purpose:** This file defines the Flask Blueprint for the administrative section of the application. It provides a wide array of tools for managing users, monitoring site activity, managing advertisements, broadcasting notifications, analyzing site performance, and configuring system-wide settings like maintenance mode.

**⚙️ Key Components & Functionality:**

*   **`admin_bp` Blueprint:**
    *   Configured with `url_prefix='/admin'`, meaning all routes defined within this Blueprint will be prefixed with `/admin`.
*   **Jinja2 Custom Filters (`get_activity_badge_color`, `get_activity_icon`):**
    *   Custom filters are registered to enhance the admin UI by providing dynamic styling (colors and icons) for different user activity types in templates.
*   **Admin Configuration:**
    *   `ADMIN_SESSION_KEY`: Defines the session key used to identify a logged-in administrator.
    *   `ADMIN_PASSWORD_HASH`: **CRITICAL SECURITY RISK:** A hardcoded hashed password for the default admin user. This should be replaced with a secure method for storing and retrieving admin credentials (e.g., environment variables, configuration files, or a dedicated admin user management system).
    *   `AD_REVENUE_RATES`: Defines the revenue generated per ad impression for different ad types.
*   **`load_user_context()` (before_request):**
    *   A `before_request` handler specific to the admin Blueprint. It loads the regular user's context (if a user is logged in) and makes it available as `g.current_user` for reference within the admin panel, allowing admins to see user-related data.
*   **`admin_required` Decorator:**
    *   A custom decorator that checks if an administrator is logged in (`ADMIN_SESSION_KEY` in session). If not, it redirects them to the admin login page. This protects all sensitive admin routes.
*   **Database Utility Functions (`get_db`, `query_db`, `execute_db`):**
    *   This file contains its own set of database utility functions, including an enhanced `get_db` that configures `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` for better concurrent access and performance with SQLite. This duplicates functionality found in `database.py` and indicates a need for refactoring and consolidation.
*   **`ensure_admin_tables()`:**
    *   A function to ensure that all admin-specific database tables exist. It creates:
        *   `admin_users`: For admin login credentials.
        *   `ad_impressions`: Tracks every ad shown to a user and its revenue.
        *   `personalized_ads`: Stores details of ads that can be displayed.
        *   `admin_activity_log`: Logs all actions performed by administrators.
        *   `user_activity`: An enhanced table for tracking user actions.
        *   `ad_display_assignments`: Manages which ads are assigned to which users.
        *   `notifications`: Stores broadcast messages.
    *   It also inserts a default "admin" user if `admin_users` table is empty.
*   **Admin Authentication Routes (`/admin/login`, `/admin/logout`):**
    *   Handles admin login. Notably, it checks only a password against the `ADMIN_PASSWORD_HASH` without a separate username field for the default admin.
    *   Handles admin logout.
*   **Dashboard (`/admin/dashboard`, `/admin/api/stats/live`, `/admin/api/activities/recent`, `/admin/api/revenue/live`):**
    *   Provides an overview of key application statistics (total users, links, visits, revenue, etc.).
    *   Includes AJAX endpoints for live statistics updates, recent user activities, and live revenue figures, suggesting a dynamic frontend.
*   **User Management (`/admin/users`, `/admin/users/<int:user_id>`, `/admin/users/<int:user_id>/delete`, `/admin/users/<int:user_id>/toggle-premium`):**
    *   Allows administrators to view, search, and paginate through users.
    *   View detailed user profiles, including their links, ads, activities, and revenue generated.
    *   Delete users and all associated data (handled carefully due to foreign key constraints).
    *   Toggle premium status for users and assign membership tiers.
*   **Ad Management (`/admin/ads`, `/admin/ads/create-for-user/<int:user_id>`, `/admin/ads/create`, `/admin/ads/<int:ad_id>/toggle`, `/admin/ads/<int:ad_id>/delete`, `/admin/ads/<int:ad_id>/display-to-users`):**
    *   Manages the creation, editing, and deletion of personalized advertisements.
    *   Ads can be global or targeted to specific users/user groups.
    *   Includes functionality for uploading image-based ads.
    *   Allows explicit assignment of ads to users.
*   **Broadcast (`/admin/broadcast`):**
    *   Enables administrators to send notifications to all users, specific user groups, or selected individual users.
*   **Analytics (`/admin/analytics`):**
    *   A detailed analytics dashboard showing revenue trends, top users, ad performance, user growth, and link creation trends over customizable date ranges.
*   **Activity Monitoring (`/admin/activity`):**
    *   Displays a paginated and filterable log of all user activities across the platform.
*   **Data Export (`/admin/export/users`, `/admin/export/revenue`):**
    *   Allows exporting user data and ad revenue summaries to CSV format.
*   **Feedback Management (`/admin/feedbacks`, `/admin/feedbacks/<int:feedback_id>/respond`, `/admin/feedbacks/<int:feedback_id>/status`, `/admin/feedbacks/<int:feedback_id>/delete`):**
    *   Provides a system for viewing, responding to, updating the status of, and deleting user feedback.
*   **Maintenance Mode (`/admin/maintenance`):**
    *   Allows administrators to enable or disable a site-wide maintenance mode and set a custom message. These settings are stored in a `system_settings` table.
*   **Helper Functions (`log_admin_activity`, `track_user_activity`, `track_ad_impression`):**
    *   These functions are designed for logging various admin actions, user activities, and ad impressions to their respective database tables, providing audit trails and data for analytics. `track_user_activity` and `track_ad_impression` are imported and used by other modules (e.g., `auth.py`, `links.py`).

**🔄 Role in Overall Application Flow:**

`admin_panel.py` is the operational backbone of the "Smart Link Intelligence" platform. It provides the tools necessary for the platform owners to manage the entire ecosystem, from user and content management to performance monitoring and monetization. Its robust feature set underscores that the application is designed as a complete business solution rather than just a simple utility. The strong coupling with other modules (e.g., `track_user_activity` being imported elsewhere) highlights its central role in monitoring and managing application events.

---

### 🤖 `chatbot.py` - AI Chat Assistant Logic

**🎯 Purpose:** This file implements the core logic for the AI Chat Assistant integrated into the "Smart Link Intelligence" platform. It's responsible for loading predefined conversational intents from a JSON file and providing responses based on user messages through keyword matching.

**⚙️ Key Components & Functionality:**

*   **`ChatBot` Class:**
    *   **`__init__(self, intents_file='intents.json')`:**
        *   Initializes the chatbot. It sets the `intents_file` (defaulting to `intents.json`) and initializes `self.intents` as an empty list.
        *   Calls `load_intents()` to populate the `self.intents` list with data from the specified JSON file.
        *   `self.last_modified`: Stores the last modification time of the `intents.json` file to enable dynamic reloading.
    *   **`load_intents(self, intents_file)`:**
        *   Handles loading (or reloading) the conversational intents from the `intents.json` file.
        *   It checks `os.path.getmtime(file_path)` to see if the file has been modified since the last load. If so, it reloads the intents, allowing for dynamic updates to the chatbot's knowledge base without restarting the application.
        *   Reads the JSON data and extracts the 'intents' array.
        *   Includes error handling for file operations.
    *   **`get_response(self, message)`:**
        *   This is the core method for processing user input and generating a response.
        *   First, it calls `load_intents()` again to ensure the latest intents are always used, in case the `intents.json` file was updated.
        *   Converts the incoming `message` to lowercase for case-insensitive matching.
        *   It iterates through each `intent` defined in `self.intents`.
        *   For each intent, it checks its `patterns` against the user's message.
        *   **Keyword Matching:** It uses a simple keyword matching approach: if a `pattern` is found within the `message`, it increments a `score`.
            *   Bonuses are given for exact matches and longer multi-word pattern matches. This helps prioritize more specific intents.
        *   It identifies the `best_intent` based on the highest score.
        *   If a `best_intent` is found with a score greater than 0, it randomly selects one of the `responses` associated with that intent.
        *   If no matching intent is found, it returns a generic fallback message.
*   **`chatbot_instance = ChatBot()`:**
    *   A singleton instance of the `ChatBot` class is created when `chatbot.py` is imported. This ensures that all parts of the application use the same chatbot instance, maintaining its state (like loaded intents) and avoiding redundant re-initializations.
*   **`get_chat_response(message)` function:**
    *   A convenience function that acts as a wrapper around `chatbot_instance.get_response(message)`, making it easier for other modules to interact with the chatbot.

**🔄 Role in Overall Application Flow:**

`chatbot.py` powers the interactive AI Assistant available across the "Smart Link Intelligence" platform. It provides instant support to users by matching their queries with predefined intents and delivering relevant, pre-scripted responses. The dynamic reloading of intents allows for easy updates to the chatbot's knowledge base without service interruption, making it a flexible component for enhancing user experience and reducing support load. It is directly used by the frontend via AJAX calls, which are handled in the `routes/main.py` (specifically `ai_chat_endpoint` function, which I would expect to find there).

---

### ⚙️ `config.py` - Application Configuration

**🎯 Purpose:** This file centralizes all the configuration constants and settings for the "Smart Link Intelligence" Flask application. It defines parameters for the database, session management, link behavior, file uploads, membership tiers, and core Flask application settings.

**⚙️ Key Components & Functionality:**

*   **Database Configuration:**
    *   `DATABASE`: Defines the absolute path to the SQLite database file (`smart_links.db`). This is constructed dynamically to be relative to the file's location.
*   **Session Configuration:**
    *   `SESSION_COOKIE_NAME`: The name of the session cookie used by the Flask application.
    *   `USER_SESSION_KEY`: The key used to store the user ID in the Flask session.
*   **Link Behavior Configuration:**
    *   `RETURNING_WINDOW_HOURS`: Defines the time window (in hours) within which a visitor is considered "returning" for progressive redirection logic.
    *   `MULTI_CLICK_THRESHOLD`: The number of clicks from a user within a certain period that flags them as "highly engaged" for behavior analysis.
    *   `SUSPICIOUS_INTERVAL_SECONDS`: The time interval used to detect suspicious click patterns.
    *   `ATTENTION_DECAY_DAYS`: The number of days after which a user's attention/engagement state might decay.
    *   `STATE_DECAY_DAYS`: Similar to `ATTENTION_DECAY_DAYS`, likely for general user state.
*   **File Upload Configuration:**
    *   `UPLOAD_FOLDER`: The absolute path where uploaded files (e.g., ad images) will be stored.
    *   `ALLOWED_EXTENSIONS`: A set of file extensions permitted for uploads.
    *   `MAX_IMAGE_SIZE`: Defines the maximum dimensions (width, height) for uploaded images.
*   **Membership Configuration (`MEMBERSHIP_TIERS`):**
    *   This is a crucial dictionary that defines the different membership plans and their associated features.
    *   Each tier (`"free"`, `"elite"`, `"elite_pro"`) specifies:
        *   `max_links`: The maximum number of links a user can create (or `float('inf')` for unlimited).
        *   `validity_days`: The duration for which links are valid (or `None` for unlimited).
        *   `name`: Display name of the tier.
        *   `custom_ads`: Boolean indicating if the tier allows custom ads.
        *   `ddos_protection`: Boolean indicating if the tier includes DDoS protection.
        *   `ad_free`: Boolean indicating if the tier provides an ad-free experience.
*   **Flask Configuration (`FLASK_CONFIG`):**
    *   A dictionary holding settings directly applied to the Flask application instance.
    *   `SECRET_KEY`: **CRITICAL:** A secret key used for session security. It attempts to load this from an environment variable (`FLASK_SECRET`) but falls back to a development-only default (`"dev-secret-change-me"`). **This fallback should be removed in production environments.**
    *   `SESSION_COOKIE_NAME`: References the `SESSION_COOKIE_NAME` defined above.
    *   `UPLOAD_FOLDER`: References the `UPLOAD_FOLDER` defined above.
    *   `MAX_CONTENT_LENGTH`: Sets the maximum size for incoming request bodies, primarily for file uploads.

**🔄 Role in Overall Application Flow:**

`config.py` acts as the central repository for all static and dynamic settings that govern the application's behavior. By importing this file, other modules can access consistent configuration values without hardcoding them directly. This promotes maintainability, makes it easier to update settings, and allows for environment-specific configurations (especially with the use of `os.environ.get()` for `SECRET_KEY`). The `MEMBERSHIP_TIERS` dictionary is particularly important as it dictates feature gating and the monetization model of the entire platform.

---

### 🗄️ `database.py` - Database Utilities and Schema Management

**🎯 Purpose:** This file provides utility functions for interacting with the SQLite database, including establishing connections, executing queries and commands, and ensuring that all necessary tables and columns exist in the database. It defines the core database schema for the application.

**⚙️ Key Components & Functionality:**

*   **`get_db()` function:**
    *   This function is responsible for getting a database connection. It uses Flask's `g` (global object within a request context) to store the database connection, ensuring that only one connection is opened per request.
    *   It connects to the SQLite database specified by the `DATABASE` constant from `config.py`.
    *   `g.db.row_factory = sqlite3.Row`: Configures the connection to return rows as `sqlite3.Row` objects, which behave like dictionaries (allowing access by column name) rather than tuples.
    *   `g.db.execute("PRAGMA journal_mode=WAL")`: Enables Write-Ahead Logging (WAL) mode for SQLite. This improves concurrency by allowing readers to continue while a writer is active, which is beneficial for web applications.
*   **`query_db(query: str, args=None, one=False)` function:**
    *   A generic function to execute SELECT queries.
    *   It takes the SQL `query` string, optional `args` (parameters for parameterized queries), and a `one` flag.
    *   If `one` is `True`, it returns only the first matching row (or `None`). Otherwise, it returns all matching rows.
    *   **Security Note:** The use of `args` for parameters is crucial for preventing SQL injection vulnerabilities.
*   **`execute_db(query: str, args=None)` function:**
    *   A generic function to execute SQL commands that modify the database (INSERT, UPDATE, DELETE, CREATE TABLE, etc.).
    *   It executes the `query` with `args` and then `commits` the transaction to save the changes.
*   **`close_db(error)` function:**
    *   This function is registered as a teardown function for the Flask application context. It's automatically called when the application context ends (typically at the end of a request).
    *   It safely closes the database connection stored in `g` if one exists.
*   **`ensure_column(table_name, column_name, column_definition)` function:**
    *   A utility function to add a column to an existing table if it doesn't already exist.
    *   It uses `ALTER TABLE ADD COLUMN` and includes error handling to catch `sqlite3.OperationalError` if the column already exists (e.g., "duplicate column name"). This is useful for schema evolution or ensuring backward compatibility.
*   **`ensure_db()` function:**
    *   This is the most critical function for database setup. It creates all the necessary tables if they don't already exist and ensures that certain columns are present in existing tables.
    *   **Table Creation (using `CREATE TABLE IF NOT EXISTS`):**
        *   `users`: Stores user authentication details, membership status, and tiers.
        *   `links`: Stores all shortened link data, including original URL, custom code, various redirection URLs, behavioral rules, and DDoS protection settings.
        *   `visits`: Records every visit to a short link, capturing extensive analytics data (IP, user agent, geolocation, device, browser, behavior, etc.).
        *   `behavior_rules`: Allows users to define custom rules for how links behave, including thresholds for interested/engaged users and DDoS rate limits.
        *   `ddos_events`: Logs specific events related to DDoS detection and protection for individual links.
        *   `system_settings`: Stores global application settings (like maintenance mode).
        *   `notification_dismissals`: Tracks which users have dismissed which notifications.
        *   `feedbacks`: Stores user feedback submitted via the contact form or similar.
    *   **Column Assurance:** After creating tables, it calls `ensure_column` multiple times to ensure various columns (like `protection_level`, `auto_disabled`, `membership_tier`, `expires_at`, and detailed DDoS rule settings) are present, which helps in incremental database updates or additions of new features.

**🔄 Role in Overall Application Flow:**

`database.py` is fundamental to the application's persistence layer. `ensure_db()` is called during application startup (`app.py`) to guarantee the database schema is correctly set up. `get_db()`, `query_db()`, and `execute_db()` are used extensively by almost all other modules (`routes`, `admin_panel`, `ddos_protection`, `utils`) to interact with the database. The `close_db()` function ensures proper resource management by closing connections after each request. It essentially provides the low-level data access and schema management for the entire "Smart Link Intelligence" platform.

---

### 🛡️ `ddos_protection.py` - DDoS Protection System

**🎯 Purpose:** This file implements a multi-layered Distributed Denial of Service (DDoS) protection system for the application's short links. It detects and mitigates malicious traffic by applying various rate-limiting rules and dynamic protection levels based on detected threats. It's a premium feature available to "Elite Pro" members.

**⚙️ Key Components & Functionality:**

*   **`ddos_bp` Blueprint:**
    *   Configured with `url_prefix='/ddos-protection'`, housing the user-facing dashboard and recovery functions for DDoS-protected links.
*   **`ddos_required` Decorator:**
    *   A custom decorator that restricts access to DDoS protection features only to users with the "elite_pro" membership tier. If a user is not an Elite Pro member, they are redirected.
*   **`DDoSProtection` Class:**
    *   **`__init__(self, database_path)`:** Initializes the DDoS protection system.
        *   `self.rate_limits`: A dictionary defining default rate-limiting thresholds (requests per IP per minute/hour, requests per link per minute, burst threshold, suspicious thresholds, DDoS thresholds). These serve as base values.
        *   `self.request_cache`: A `defaultdict(list)` used as an in-memory cache to store timestamps of recent requests for rate-limiting calculations. **Note:** This in-memory cache is a bottleneck for horizontal scaling; a distributed cache (e.g., Redis) would be needed for multi-instance deployments.
    *   **`get_link_rules(self, link_id)`:**
        *   Retrieves specific DDoS rules configured for a given `link_id` from the `behavior_rules` table in the database. This allows users to customize protection settings for individual links. If no custom rules are found, it uses the default `self.rate_limits`.
    *   **`check_rate_limit(self, ip_address, link_id=None)`:**
        *   The primary function for real-time rate limiting.
        *   **Load Testing Bypass:** Critically, it includes logic to bypass rate limiting if the request's User-Agent or a custom `X-Load-Test` header indicates a legitimate load test. This prevents false positives during performance testing.
        *   Checks for IP-based rate limits (requests per minute/hour) against the configured (or custom link-specific) thresholds.
        *   Detects "burst attacks" (many requests in a short time window).
        *   Logs DDoS events (`_log_ddos_event`) if rate limits are exceeded.
        *   Adds the current request timestamp to the `self.request_cache`.
    *   **`detect_ddos_attack(self, link_id)`:**
        *   Analyzes the overall traffic pattern for a specific link to detect a full-blown DDoS attack.
        *   Also includes load testing bypass.
        *   Queries the `visits` table to count recent suspicious activities and overall request rates for the given link.
        *   Compares these counts against configured `ddos_threshold`, `requests_per_link_per_minute`, and `suspicious_threshold` values to determine a `protection_level`.
    *   **`apply_protection(self, link_id, protection_level)`:**
        *   Splies different mitigation strategies based on the calculated `protection_level`:
            *   `protection_level >= 3`: Requires CAPTCHA.
            *   `protection_level >= 4`: Temporarily disables the link (e.g., for 1 hour).
            *   `protection_level >= 5`: Permanently disables the link (`auto_disabled = 1`).
        *   Updates the `links` table with the current `protection_level` and `ddos_detected_at` timestamp.
        *   Logs the protection action to `ddos_events`.
    *   **`is_link_protected(self, link_id)`:**
        *   Checks the current protection status of a link by querying the `links` table.
        *   Automatically resets temporary disables if their duration has expired.
    *   **`_cleanup_cache(self, now)`:**
        *   Periodically removes old request entries from the `self.request_cache` to prevent it from growing indefinitely.
    *   **`_log_ddos_event(self, link_id, event_type, severity, ip_address=None)`:**
        *   Internal helper to record DDoS-related events in the `ddos_events` database table.
    *   **`_reset_protection(self, link_id)`:**
        *   Resets a link's protection level and `ddos_detected_at` status in the database.
    *   **`get_protection_stats(self, link_id)`:**
        *   Retrieves aggregated statistics about DDoS events for a specific link from the `ddos_events` table.
*   **DDoS Protection Routes (`/ddos-protection/`, `/ddos-protection/recover/<int:link_id>`, `/ddos-protection/stats/<int:link_id>`):**
    *   **`ddos_protection_dashboard()`:** Displays a dashboard for Elite Pro users to view the protection status of their links and recent DDoS events.
    *   **`recover_link()`:** Allows Elite Pro users to manually reset the protection level of a disabled link.
    *   **`ddos_link_stats()`:** Provides detailed statistics and a log of DDoS events for a specific link.

**🔄 Role in Overall Application Flow:**

`ddos_protection.py` is a critical security module that safeguards the application's core functionality (link redirection) from malicious attacks. It operates by actively monitoring traffic, identifying suspicious patterns, and dynamically applying countermeasures. Its integration into the `links` redirection process (`routes/links.py` will likely use `DDoSProtection.check_rate_limit` and `DDoSProtection.detect_ddos_attack`) is essential for maintaining service availability and integrity for premium users. The user-facing dashboard provides transparency and control to Elite Pro members regarding the security of their links.

---

### 🔐 `decorators.py` - Custom Authentication and Authorization Decorators

**🎯 Purpose:** This file defines custom Python decorators used throughout the Flask application to enforce authentication and authorization rules on routes. Decorators provide a clean and reusable way to add functionality to functions (in this case, Flask view functions) without modifying their core logic.

**⚙️ Key Components & Functionality:**

*   **`login_required(fn)` decorator:**
    *   **Functionality:** Ensures that the user accessing the decorated route is authenticated (i.e., a user object exists in `flask.g.user`).
    *   **Behavior:** If `g.user` is not set (meaning no user is logged in), it flashes a warning message and redirects the user to the login page (`url_for("login")`).
    *   **Usage:** Applied to routes that require a regular user to be logged in.
*   **`login_or_admin_required(fn)` decorator:**
    *   **Functionality:** Provides a more flexible authentication check, allowing access to the decorated route if either a regular user is logged in (`g.user`) OR an administrator is logged in (`session.get("admin_uid")`).
    *   **Behavior:** If neither a regular user nor an admin is logged in, it flashes a warning and redirects to the regular user login page.
    *   **Usage:** Useful for routes that might be accessible by both regular users and administrators, or if there's a common shared resource that either can manage.
*   **`@wraps(fn)`:**
    *   Both decorators use `@wraps(fn)` from `functools`. This is a standard Python practice when creating decorators. It preserves the original function's metadata (like `__name__`, `__doc__`, `__module__`), which is important for debugging and introspection, especially within frameworks like Flask.

**🔄 Role in Overall Application Flow:**

`decorators.py` plays a crucial role in the application's security and access control by abstracting away common authentication checks. Instead of writing the same `if` statements in every protected view function, developers can simply apply these decorators. This makes the code cleaner, more readable, and less prone to errors in implementing security checks. These decorators are typically imported and used within the various Blueprint files in the `routes/` directory.

---

### 🧰 `utils.py` - Utility Functions

**🎯 Purpose:** This file consolidates a collection of helper functions used across various modules of the "Smart Link Intelligence" application. These utilities cover diverse areas such as hashing, code generation, session management, email sending, user behavior classification, suspicious activity detection, geolocation, and user agent parsing.

**⚙️ Key Components & Functionality:**

*   **Core Utilities:**
    *   **`utcnow()`:** Returns the current UTC datetime. Essential for consistent timestamping across the application.
    *   **`hash_value(value: str)`:** Generates an SHA256 hash of a given string. Used for hashing sensitive data like IP addresses (for privacy) and potentially link passwords.
    *   **`generate_code(length: int = 6)`:** Generates a random alphanumeric string of a specified length. Used for creating short link codes.
    *   **`ensure_session()`:** Ensures a unique session ID (`sid`) exists for the current user in the Flask session. If not present, it generates a new UUID and stores it. This is crucial for tracking user sessions.
    *   **`get_link_password_hash(link)`:** Safely extracts the password hash from a link object, handling cases where it might be missing.
*   **Email Sending (`send_email`):**
    *   Sends emails using SMTP (specifically `smtp.gmail.com`).
    *   Retrieves `EMAIL_USER` and `EMAIL_PASS` from environment variables, falling back to mock printing if credentials are not set (good for development).
    *   Supports HTML content in emails.
*   **Behavior Classification (`classify_behavior`):**
    *   Analyzes a user's `visits` to a specific link to classify their behavior (`"Curious"`, `"Interested"`, `"Highly engaged"`).
    *   Uses thresholds defined in `config.py` (or custom `behavior_rule` settings):
        *   `RETURNING_WINDOW_HOURS`: How long a user is considered "returning".
        *   `MULTI_CLICK_THRESHOLD`: Number of clicks to be considered "highly engaged".
    *   Returns the classified behavior and the total number of visits for the session.
*   **Suspicious Activity Detection (`detect_suspicious`):**
    *   Identifies potential bot activity or rapid-fire requests.
    *   **Load Testing Bypass:** Similar to `ddos_protection.py`, it intelligently bypasses detection for requests from known load testing tools or those explicitly marked with `X-Load-Test` header.
    *   Checks for:
        *   Extremely rapid requests from the same IP (e.g., < 0.3 seconds apart).
        *   Burst patterns (e.g., 8+ requests in 1 second).
    *   **Note:** The comment indicates an increased threshold for suspicious hits to avoid interfering with DDoS testing, suggesting active refinement of these heuristics.
*   **Target Decider (`decide_target`):**
    *   Determines the final redirect URL for a link based on its `behavior_rule` (e.g., "progression", "standard") and the user's classified `behavior` and `session_count`. This is a core part of the "Smart Link" functionality.
*   **Link State Evaluation (`evaluate_state`):**
    *   Assesses the "health" or activity level of a link (`"Active"`, `"Decaying"`, `"Inactive"`, `"High Interest"`).
    *   Considers factors like days since the last visit, number of suspicious hits, and recent activity count.
*   **Trust Score Calculation (`trust_score`):**
    *   Calculates a numerical trust score for a link based on the ratio of total visits, suspicious visits, and engaged visits. Higher engagement and lower suspicious activity lead to a higher trust score.
*   **Attention Decay Analysis (`attention_decay`):**
    *   Aggregates visit data by day to show how a link's attention (visits) decays over time. Useful for analytics visualization.
*   **User Agent Parsing:**
    *   **`detect_device(user_agent: str)`:** Extracts the device type (`"Mobile"`, `"Tablet"`, `"Desktop"`) from the User-Agent string.
    *   **`parse_browser(user_agent: str)`:** Identifies the browser and its version (e.g., "Chrome (120)", "Firefox (115)").
    *   **`parse_os(user_agent: str)`:** Determines the operating system (e.g., "Windows 10/11", "macOS 14.2", "Android 13").
*   **Geolocation & ISP Information:**
    *   **`geo_cache`:** A simple in-memory cache for geolocation results to reduce API calls. (Acknowledged as needing a distributed cache in production).
    *   **`get_client_ip()`:** Safely retrieves the client's real IP address, handling common proxy headers (`X-Forwarded-For`, `X-Real-IP`).
    *   **`get_public_ip_fallback()`:** Fetches the server's own public IP, useful when testing with private IPs.
    *   **`get_api_location(ip: str)`:** Retrieves detailed geolocation data (country, city, lat/lon, timezone, ISP, organization) for an IP address. It uses `ip2location.io` as the primary API and `ip-api.com` as a fallback. It handles private IPs by trying to find the public IP.
    *   **`detect_region(ip: str)`:** Provides a concise region string (e.g., "New York, United States").
    *   **`get_detailed_location(ip: str)`:** Returns a dictionary with detailed location information.
    *   **`country_to_continent(country: str)`:** Maps a country name to its respective continent.
    *   **`normalize_isp(isp_name: str)`:** Standardizes common ISP names to prevent data fragmentation in analytics.
    *   **`get_isp_info(ip: str)`:** Combines DNS reverse lookup and API calls to get ISP, hostname, and organization details for an IP.

**🔄 Role in Overall Application Flow:**

`utils.py` acts as a crucial support module, centralizing many of the intelligent and data-enriching functionalities that define the "Smart Link Intelligence" platform. Its functions are extensively used by the `links` module for redirection logic, by the `admin_panel` for analytics, and by various other parts of the application for general-purpose tasks like email notifications. It directly contributes to the "smartness" of the links by enabling behavioral tracking, threat detection, and detailed visitor insights.

---

### 🛂 `routes/auth.py` - User Authentication Routes

**🎯 Purpose:** This file defines the Flask Blueprint for all user authentication-related functionalities, including user registration (signup), login, logout, and AJAX-based availability checks for usernames and emails.

**⚙️ Key Components & Functionality:**

*   **`auth_bp` Blueprint:**
    *   Creates a Flask Blueprint named `auth` to group all authentication routes under a common module.
*   **`signup()` Route (`/signup`, methods=["GET", "POST"]):**
    *   Handles user registration.
    *   **Input Validation:** Performs extensive server-side validation for:
        *   Required fields (username, password, email, terms acceptance).
        *   Username format (alphanumeric, underscores, 3-20 characters) and uniqueness (case-insensitive).
        *   Email format and uniqueness.
        *   Password complexity (minimum length, uppercase, lowercase, number, special character).
        *   Password confirmation matching.
    *   **User Creation:** If all validations pass, it hashes the password using `generate_password_hash` from `werkzeug.security` and inserts the new user's details into the `users` table.
    *   **Welcome Email:** Sends a formatted HTML welcome email to the newly registered user using the `send_email` utility from `utils.py`.
    *   **Auto-Login:** Automatically logs in the new user by setting their `id` in the session.
    *   **Activity Tracking:** Records the user registration event using `admin_panel.track_user_activity`.
    *   **Error Handling:** Catches `sqlite3.IntegrityError` for duplicate username/email and generic `Exception` for other issues, displaying appropriate flash messages to the user.
    *   **Rendering:** Renders the `signup.html` template.
*   **`check_availability()` Route (`/check-availability`, methods=["POST"]):**
    *   An AJAX endpoint designed for client-side validation of username and email availability during signup.
    *   Receives `field_type` ("username" or "email") and `value` in a JSON request.
    *   Performs validation for format and uniqueness against the database.
    *   Returns a JSON response indicating `available: True/False` and a `message`.
*   **`login()` Route (`/login`, methods=["GET", "POST"]):**
    *   Handles user login.
    *   **Input Validation:** Checks if username/email and password fields are provided.
    *   **Admin Redirection:** If the input username/email is "admin" (case-insensitive), it redirects to the admin login page (`admin.admin_login`), separating admin and user login flows.
    *   **User Lookup:** Attempts to find a user by either username or email in the `users` table.
    *   **Password Verification:** Uses `check_password_hash` from `werkzeug.security` to verify the provided password against the stored hash.
    *   **Login Success:** If credentials are valid, it sets the user's `id` in the session (`session[USER_SESSION_KEY]`).
    *   **"Remember Me" Functionality:** If the "remember_me" checkbox is selected, it makes the session permanent and extends its lifetime to 30 days.
    *   **Activity Tracking:** Records the user login event using `admin_panel.track_user_activity`.
    *   **Rendering:** Renders the `login.html` template.
*   **`logout()` Route (`/logout`):**
    *   Handles user logout by removing the `USER_SESSION_KEY` from the session.
    *   Flashes an info message and redirects to the login page.

**🔄 Role in Overall Application Flow:**

`routes/auth.py` is fundamental for user management and access control. It provides the secure and validated entry points for users to interact with the application. Its integration with `utils.send_email` for welcome messages and `admin_panel.track_user_activity` for auditing user actions demonstrates its interconnectedness with other core modules. The separation of admin and user login is a thoughtful design choice for security.

---

### 🔗 `routes/links.py` - Link Management and Redirection Routes

**🎯 Purpose:** This file defines the Flask Blueprint responsible for all operations related to link creation, intelligent redirection, password protection, analytics display, and data export. It is the central hub for the "Smart Link Intelligence" platform's core functionality.

**⚙️ Key Components & Functionality:**

*   **`links_bp` Blueprint:**
    *   Groups all link-related routes, making the application modular.
*   **`create()` Route (`/create`, methods=["POST"]):**
    *   **Decorator:** `@login_required` ensures only authenticated users can create links.
    *   **Membership Limits:** Checks the user's `membership_tier` (from `g.user`) against `MEMBERSHIP_TIERS` in `config.py` to enforce `max_links` limits.
    *   **Expiration:** Sets an `expires_at` timestamp based on the `validity_days` of the user's tier.
    *   **Feature Gating:** For free users, it automatically downgrades "progression" or "password_protected" `behavior_rule` requests to "standard", enforcing tier-based feature restrictions.
    *   **URL Validation:** Ensures a `primary_url` is provided.
    *   **Custom Code:** Allows users to specify a `code` (custom alias) or generates one using `utils.generate_code()`. Checks for code uniqueness.
    *   **Password Protection:** If a password is provided, it hashes it using `generate_password_hash` and stores the hash.
    *   **Database Insertion:** Inserts the new link's details into the `links` table.
    *   **Activity Tracking:** Logs the link creation using `admin_panel.track_user_activity`.
    *   **UX:** Stores the full shortened link in `session['new_link']` to display it prominently on the dashboard after creation.
*   **`redirect_link()` Route (`/r/<code>`):**
    *   This is the most critical route, handling all incoming short link requests.
    *   **Link Lookup:** Retrieves the link details from the database using the provided `code`.
    *   **Password Protected Check:** If the link has a `password_hash`, it redirects the user to the `/p/<code>` route for password entry.
    *   **Expiration Check:** Verifies if the link has expired.
    *   **DDoS Protection (for Elite Pro owners):**
        *   Retrieves the link owner's membership tier and checks if `ddos_protection` is enabled for that tier.
        *   Initializes `DDoSProtection` from `ddos_protection.py`.
        *   Checks `is_link_protected()`: If the link is already under active protection (disabled, temporarily disabled, or CAPTCHA required), it renders `ddos_blocked.html` with an appropriate message.
        *   Performs `check_rate_limit()`: If the IP is rate-limited or suspected of a burst attack, it blocks access and renders `ddos_blocked.html`.
        *   Executes `detect_ddos_attack()`: Continuously monitors for DDoS patterns and, if detected, applies the necessary protection (`ddos_protection.apply_protection()`), potentially leading to blocking.
    *   **Visitor Data Collection:**
        *   Collects extensive data about the visitor: `ip_address` (via `utils.get_client_ip`), `session_id` (via `utils.ensure_session`), `user_agent`, `referrer`.
        *   Uses `utils` functions for:
            *   `detect_region`, `get_detailed_location` (country, city, lat/lon, timezone).
            *   `parse_browser`, `parse_os` (from User-Agent).
            *   `get_isp_info` (ISP, hostname, organization).
    *   **Behavior Classification:**
        *   Retrieves recent `visits` to the link.
        *   Uses `utils.classify_behavior()` to determine the user's engagement level.
        *   Uses `utils.detect_suspicious()` to flag potentially bot-like activity.
    *   **Target URL Decision:** Uses `utils.decide_target()` to select the final redirection URL based on the link's `behavior_rule` and the classified user behavior.
    *   **Visit Logging:** Inserts all collected visitor data into the `visits` table.
    *   **Link State Evaluation:** Updates the `links` table's `state` (e.g., "Active", "Decaying", "Inactive") based on recent activity using `utils.evaluate_state()`.
    *   **Ad Handling:**
        *   Checks if the user explicitly requested to skip ads (`direct=true`).
        *   Checks if the link owner's membership tier grants an ad-free experience (`ad_free` from `MEMBERSHIP_TIERS`).
        *   If ads are to be skipped, redirects directly to `target_url`.
        *   Otherwise, redirects to `links.show_ads` to display ads before the final redirection.
*   **`show_ads()` Route (`/ads/<code>`):**
    *   Displays a page with personalized ads before redirecting the user to the `target_url`.
    *   **Ad Selection:** Fetches active `personalized_ads` from the database that are either owned by the link's user, specifically assigned to them, or are global ads.
    *   **Randomization:** Randomly selects ads to display in different positions (large ad for position 1, small ads for positions 2 and 3).
    *   **Ad Impression Tracking:** Logs each ad impression using `admin_panel.track_ad_impression()`, which also calculates and records revenue.
*   **`password_protected()` Route (`/p/<code>`, methods=["GET", "POST"]):**
    *   Handles the page where users enter a password for protected links.
    *   **Password Verification:** On POST, it verifies the entered password against the stored `password_hash` using `check_password_hash`.
    *   **Redirection after Success:** If correct, it performs the full visit logging, behavior classification, and ad handling logic (similar to `redirect_link`) before redirecting the user to the `target_url` (or `show_ads`).
*   **`delete_link()` Route (`/delete-link/<int:link_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required` ensures only logged-in users can delete links.
    *   **Ownership Check:** Verifies that the `link_id` belongs to the current `g.user`.
    *   **Database Deletion:** Deletes associated `visits` and `ddos_events` before deleting the link itself (due to foreign key constraints).
    *   **Activity Tracking:** Logs the link creation using `admin_panel.track_user_activity`.
*   **`analytics()` Route (`/links/<code>`):**
    *   **Decorator:** `@login_or_admin_required` allows both users and admins to view analytics.
    *   **Data Aggregation:** Retrieves all `visits` for a specific link.
    *   **Behavior Recalculation:** Recalculates behavior (`"Curious"`, `"Interested"`, `"Highly engaged"`) for each visit, applying the link's (or user's default) `behavior_rule` thresholds.
    *   **Metrics Calculation:** Computes total visits, unique visitors (based on `ip_hash`), suspicious visit count, and counts for each behavior category.
    *   **Geographic Data:** Aggregates visit data by region (continent) and city.
    *   **ISP and Device Distribution:** Analyzes ISP and device usage from visit data.
    *   **Time-based Trends:** Calculates daily and hourly engagement trends.
    *   **Trust Score:** Displays the `trust_score` (from `utils.trust_score`) for the link.
    *   **Analytics Payload:** Prepares a JSON `analytics_payload` for client-side charting.
    *   **Detailed Visitors:** Lists recent detailed visitor information (similar to a "Grabify" log).
    *   **Rendering:** Renders the `analytics.html` template with all the aggregated data.
*   **`analytics_overview()` Route (`/analytics-overview`):**
    *   **Decorator:** `@login_required`
    *   Provides a high-level overview of all links for the current user.
    *   Displays total clicks and unique visitors across all user's links.
    *   Prepares `chart_data` for a link status distribution chart.
    *   Tracks activity using `admin_panel.track_user_activity`.
    *   Renders `analytics_overview.html`.
*   **`export_csv()` Route (`/links/<code_id>/csv`):**
    *   Exports a summary of link analytics data (totals, region, city, device, hourly) to a CSV file.
    *   Includes logic to normalize ISP names and map countries to continents for the export.
    *   Logs the export activity.
*   **`export_link_analytics_excel()` Route (`/links/<code_id>/export-excel`):**
    *   Exports a detailed visitor log (IP, country, city, browser, ISP, coordinates, etc.) as an Excel-compatible HTML table.
    *   Logs the export activity.

**🔄 Role in Overall Application Flow:**

`routes/links.py` is the operational core of the "Smart Link Intelligence" platform. It manages the entire lifecycle of a short link, from creation and intelligent redirection to comprehensive analytics and secure access. It heavily relies on `utils.py` for data processing and `ddos_protection.py` for security, demonstrating deep integration across the application's modules. Its analytics capabilities are a key selling point, offering users deep insights into their link performance.

---

### 🏠 `routes/main.py` - Core Public and User Interface Routes

**🎯 Purpose:** This file defines the Flask Blueprint for the main public-facing pages, the user dashboard, and general utilities like documentation, contact form handling, and the AI chat endpoint. It acts as the primary interface for both unauthenticated visitors and authenticated users.

**⚙️ Key Components & Functionality:**

*   **`main_bp` Blueprint:**
    *   Creates a Flask Blueprint named `main` for general application routes.
*   **`landing()` Route (`/`):**
    *   Serves as the application's homepage.
    *   If a user is already logged in (`g.user` is set), it automatically redirects them to their dashboard (`main.index`).
    *   Otherwise, it renders the `landing.html` template.
*   **`maintenance()` Route (`/maintenance`):**
    *   A public page displayed when the application is in maintenance mode.
    *   Crucially, it clears the user's session (`session.pop(USER_SESSION_KEY, None)`) and clears `g.user` to ensure no user-specific data is accessible during maintenance and forces re-login after maintenance ends.
    *   Retrieves a custom maintenance message from the `system_settings` table, falling back to a default message if not found or if the table is unavailable.
    *   Renders the `maintenance.html` template.
*   **`index()` Route (`/dashboard`):**
    *   **Decorator:** `@login_required` ensures only authenticated users can access their dashboard.
    *   **User Links:** Fetches all short links created by the current user from the `links` table.
    *   **Link Status Stats:** Aggregates link status (`"Active"`, `"Inactive"`, etc.) for charting on the dashboard.
    *   **Behavior Rules:** Retrieves custom behavior rules defined by the user.
    *   **New Link Notification:** Checks for a `new_link` in the session (set after successful link creation in `routes/links.py`) to display a success message and the new link.
    *   **Membership Tier Info:** Retrieves and displays details about the user's current membership tier (e.g., `max_links` allowance) from `MEMBERSHIP_TIERS` in `config.py`.
    *   **Activity Tracking:** Records the dashboard view event using `admin_panel.track_user_activity`.
    *   **Rendering:** Renders the `index.html` template, passing all necessary data for the dashboard UI.
*   **`documentation()` Route (`/documentation`):**
    *   Serves a static documentation page.
    *   Renders the `documentation.html` template.
*   **`contact()` Route (`/contact`, methods=["POST"]):**
    *   Handles submissions from the contact form on the landing page.
    *   **Validation:** Performs basic validation on `name`, `email`, `subject`, and `message` fields.
    *   **Database Insertion:** Inserts the feedback into the `feedbacks` table with a `status` of "new".
    *   Returns a JSON response indicating success or failure.
*   **`chat()` Route (`/chat`, methods=["POST"]):**
    *   The API endpoint for the AI Chat Assistant.
    *   Receives a user `message` via a JSON POST request.
    *   Delegates the message processing to `chatbot.get_chat_response()`.
    *   **Activity Tracking:** Records interactions with the AI chatbot using `admin_panel.track_user_activity` if a user is logged in.
    *   Returns the chatbot's `response` in JSON format.

**🔄 Role in Overall Application Flow:**

`routes/main.py` is central to the user's journey through the application. It manages the initial entry point, provides the personalized user dashboard, and handles generic support functionalities. Its close ties to `config.py` for membership information, `database.py` for data retrieval, and `chatbot.py` for AI interactions illustrate how different modules are integrated to provide a cohesive user experience. It effectively guides both unauthenticated visitors and authenticated users through the primary functions and information of the "Smart Link Intelligence" platform.

---

### 📢 `routes/ads.py` - Advertisement Management Routes

**🎯 Purpose:** This file defines the Flask Blueprint for managing user-created personalized advertisements. It allows "Elite Pro" members to create, view, toggle the status of, and delete custom ads that can be displayed on shortened links.

**⚙️ Key Components & Functionality:**

*   **`ads_bp` Blueprint:**
    *   Creates a Flask Blueprint named `ads` for all advertisement-related routes.
*   **`create_ad()` Route (`/create-ad`):**
    *   **Decorator:** `@login_required` ensures only authenticated users can access this page.
    *   **Membership Check:** Crucially, it verifies that the logged-in user's `membership_tier` (from `g.user`) has `custom_ads` enabled according to `config.MEMBERSHIP_TIERS`. If not an "Elite Pro" member, it flashes a warning and redirects them, enforcing feature gating.
    *   **Existing Ads:** Retrieves and displays all existing personalized ads belonging to the current user.
    *   **Ad Statistics:** Calculates and displays the total and active ads for the user.
    *   **Activity Tracking:** Records the ad management view using `admin_panel.track_user_activity`.
    *   **Rendering:** Renders the `create_ad.html` template, which likely contains the form for creating new ads and a list of existing ones.
*   **`submit_ad()` Route (`/create-ad/submit`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   **Membership Check:** Re-validates the user's membership tier to ensure they are authorized to create custom ads.
    *   **Form Data:** Processes the submitted form data for the new ad, including `title`, `description`, `cta_text` (Call To Action text), `cta_url` (Call To Action URL), `grid_position`, and `ad_type`.
    *   **Validation:**
        *   Checks for required text fields.
        *   Validates that `cta_url` starts with `http://` or `https://`.
        *   Validates `grid_position` to be one of the allowed values (1, 2, or 3).
    *   **Image Upload (for `ad_type == "image"`):**
        *   Handles the upload of an image file (`ad_image`).
        *   Calls `process_and_save_image()` to securely save the file and return its unique filename.
    *   **Custom Ad Details (for `ad_type != "image"`):** Collects `background_color`, `text_color`, and `icon` for custom ads.
    *   **Database Insertion:** Inserts the ad's details into the `personalized_ads` table, associating it with the current user.
    *   **Activity Tracking:** Logs the ad creation using `admin_panel.track_user_activity`.
*   **`uploaded_file()` Route (`/uploads/<filename>`):**
    *   Serves uploaded files (e.g., ad images) from the `UPLOAD_FOLDER` configured in `app.py`. This allows the browser to fetch images directly.
*   **`toggle_ad()` Route (`/toggle-ad/<int:ad_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   **Ownership Check:** Verifies that the `ad_id` belongs to the current `g.user` before allowing modification.
    *   **Status Update:** Toggles the `is_active` status of the specified ad in the `personalized_ads` table.
    *   **Activity Tracking:** Logs the ad status change using `admin_panel.track_user_activity`.
*   **`delete_ad()` Route (`/delete-ad/<int:ad_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   **Ownership Check:** Verifies that the `ad_id` belongs to the current `g.user` before allowing modification.
    *   **Database Deletion:** Deletes the specified ad from the `personalized_ads` table.
    *   **Activity Tracking:** Logs the ad deletion using `admin_panel.track_user_activity`.
*   **`process_and_save_image(file, user_id)` function:**
    *   A helper function for handling image uploads.
    *   Uses `werkzeug.utils.secure_filename` to sanitize filenames.
    *   Generates a unique filename using `uuid.uuid4()`.
    *   Saves the uploaded file to the configured `UPLOAD_FOLDER`.

**🔄 Role in Overall Application Flow:**

`routes/ads.py` enables the application's monetization strategy by allowing premium users to create and manage their own personalized advertisements. It integrates tightly with the `config.py` for membership tier definitions, `database.py` for data persistence, and `admin_panel.py` for activity logging. This module provides the backend logic for a key "Elite Pro" feature, contributing to the platform's advanced capabilities and revenue generation.

---

### 👤 `routes/user.py` - User Account Management Routes

**🎯 Purpose:** This file defines the Flask Blueprint for all user-specific functionalities, including managing account settings, preferences, notifications, upgrading membership plans, and defining custom behavior rules.

**⚙️ Key Components & Functionality:**

*   **`user_bp` Blueprint:**
    *   Creates a Flask Blueprint named `user` to group all user-specific routes.
*   **`settings()` Route (`/settings`):**
    *   **Decorator:** `@login_required` ensures only authenticated users can access their settings.
    *   Retrieves user statistics (total links, total clicks).
    *   **Activity Tracking:** Records the settings page view using `admin_panel.track_user_activity`.
    *   Renders the `settings.html` template.
*   **`update_settings()` Route (`/settings/update`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Handles updates to user email and password.
    *   **Email Update:** Updates the user's email in the `users` table.
    *   **Password Update:**
        *   Requires the `current_password` to be provided and validated against the stored hash using `check_password_hash`.
        *   If valid, hashes and updates the `new_password` using `generate_password_hash`.
    *   **Activity Tracking:** Records the settings update using `admin_panel.track_user_activity`.
*   **`update_preferences()` Route (`/settings/preferences`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   A placeholder route for updating user preferences. Currently, it just flashes a success message and logs the activity. In a full implementation, this would save user-specific preference data to the database.
    *   **Activity Tracking:** Records preference updates using `admin_panel.track_user_activity`.
*   **`delete_account()` Route (`/settings/delete-account`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Provides functionality for users to delete their own accounts.
    *   **Confirmation:** Requires the user to confirm their username and password.
    *   **Data Deletion:** Upon successful confirmation, it systematically deletes all associated user data from the database, including `visits`, `links`, `personalized_ads`, and finally the `users` entry itself. This is handled carefully to respect foreign key constraints.
    *   **Session Clear:** Clears the user's session and redirects to the login page.
*   **`notifications()` Route (`/notifications`):**
    *   **Decorator:** `@login_required`
    *   Retrieves notifications relevant to the current user. This includes:
        *   Notifications explicitly targeted to the user (`target_user_id`).
        *   Global notifications (`target_group = 'all'`).
        *   Notifications targeted to their membership tier (`target_group = user_tier`).
        *   It filters out notifications that the user has already dismissed.
    *   **Activity Tracking:** Records the notification center view using `admin_panel.track_user_activity`.
    *   Renders the `notifications.html` template.
*   **`delete_notification()` Route (`/delete-notification/<int:notification_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Allows a user to dismiss a specific notification.
    *   Performs security checks to ensure the notification is indeed relevant to the current user.
    *   Records the dismissal in the `notification_dismissals` table.
    *   **Activity Tracking:** Records the notification dismissal using `admin_panel.track_user_activity`.
*   **`upgrade()` Route (`/upgrade`):**
    *   **Decorator:** `@login_required`
    *   Displays the membership upgrade page.
    *   **Activity Tracking:** Records the upgrade page view using `admin_panel.track_user_activity`.
    *   Renders the `upgrade.html` template.
*   **`process_upgrade()` Route (`/upgrade/process`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   A demo implementation for processing membership upgrades. In a real application, this would integrate with a payment gateway.
    *   **Tier Update:** Updates the user's `is_premium`, `membership_tier`, and `premium_expires_at` fields in the `users` table based on the selected plan.
    *   **Activity Tracking:** Records the upgrade event using `admin_panel.track_user_activity`.
*   **`behavior_rules()` Route (`/behavior-rules`):**
    *   **Decorator:** `@login_required`
    *   Displays and manages the user's custom behavior rules.
    *   If no custom rules exist, it automatically creates a default rule for the user, populating it with default thresholds for behavior classification and DDoS settings.
    *   **Activity Tracking:** Records the behavior rules view using `admin_panel.track_user_activity`.
    *   Renders the `behavior_rules.html` template.
*   **`create_behavior_rule()` Route (`/behavior-rules/create`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Handles the creation of new custom behavior rules.
    *   **Validation:** Validates input parameters for the rule (name, thresholds, DDoS settings).
    *   **Rule Limit:** Enforces a limit on the number of custom rules a user can create (currently 5).
    *   **Database Insertion:** Inserts the new rule into the `behavior_rules` table.
    *   **Activity Tracking:** Records the rule creation using `admin_panel.track_user_activity`.
*   **`delete_behavior_rule()` Route (`/behavior-rules/delete/<int:rule_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Allows users to delete their custom behavior rules.
    *   **Ownership Check:** Verifies that the rule belongs to the current user.
    *   **Default Rule Protection:** Prevents deletion of the only remaining rule if it's the default.
    *   **Activity Tracking:** Records the rule deletion using `admin_panel.track_user_activity`.
*   **`set_default_behavior_rule()` Route (`/behavior-rules/set-default/<int:rule_id>`, methods=["POST"]):**
    *   **Decorator:** `@login_required`
    *   Allows users to designate one of their custom rules as the default.
    *   **Ownership Check:** Verifies rule ownership.
    *   **Default Update:** Unsets the `is_default` flag for all other rules of the user before setting the selected rule as default.
    *   **Activity Tracking:** Records the default rule change using `admin_panel.track_user_activity`.

**🔄 Role in Overall Application Flow:**

`routes/user.py` is essential for providing users with control over their account, membership, and how their links behave. It's a highly interactive module that directly impacts the user experience and the core features they access. It extensively utilizes `database.py` for persistence, `decorators.py` for access control, `config.py` for membership logic, and `admin_panel.track_user_activity` for auditing user actions.

---

### 🧠 `intents.json` - Chatbot Conversational Intents

**🎯 Purpose:** This JSON file serves as the knowledge base for the `ChatBot` (implemented in `chatbot.py`). It defines a structured collection of conversational intents, each representing a specific user query or topic the chatbot is designed to understand and respond to.

**Structure:**

The file contains a single top-level key, `"intents"`, which is an array of intent objects. Each intent object has the following keys:

*   **`"tag"` (string):** A unique identifier or name for the intent (e.g., "greeting", "features", "security"). This tag is used internally by the chatbot to identify the recognized topic.
*   **`"patterns"` (array of strings):** A list of example phrases or keywords that a user might say to express this intent. The chatbot uses these patterns for keyword matching to determine the user's intention.
*   **`"responses"` (array of strings):** A list of predefined, canned responses from which the chatbot will randomly select one to answer the user's query if this intent is recognized.

**Example Intent Breakdown (from `intents.json`):**

```json
{
  "tag": "security",
  "patterns": [
    "Is it secure?",
    "DDoS protection",
    "security features",
    "Is it safe?",
    "hackers",
    "security",
    "protection",
    "how secure is it?"
  ],
  "responses": [
    "Security is our top priority! We provide enterprise-grade 5-layer DDoS protection that includes rate limiting, burst detection, IP filtering, and automatic link protection. Our system can temporarily disable links under attack and restore them when safe, ensuring your links and data are always protected.",
    "Yes, absolutely secure! Our 5-layer DDoS protection system automatically detects and mitigates attacks in real-time. We use advanced encryption, real-time threat detection, and enterprise-grade security measures to keep your links safe from any threats."
  ]
}
```

In this example:
*   If a user's message contains phrases like "Is it secure?", "DDoS protection", or "security features", the chatbot will likely identify the "security" intent.
*   It will then pick one of the two provided responses randomly to deliver to the user.

**🔄 Role in Overall Application Flow:**

`intents.json` is the configuration data for the AI Chat Assistant. The `chatbot.py` module loads this file to understand what topics it can discuss and how to respond. The dynamic reloading capability in `chatbot.py` means that this file can be updated to add new questions, refine existing patterns, or change responses without requiring a full application restart, making the chatbot's knowledge base easily maintainable and expandable. It directly contributes to the user support and information delivery aspects of the platform.

---

### 📦 `requirements.txt` - Project Dependencies

**🎯 Purpose:** This file lists all the external Python libraries and their exact versions that are required for the "Smart Link Intelligence" application to run correctly. It is a standard practice in Python development to use a `requirements.txt` file to manage project dependencies.

**Content:**

Each line in the `requirements.txt` file specifies a Python package and its pinned version, ensuring that the development, testing, and production environments use the exact same set of dependencies, which helps prevent compatibility issues.

*   **`Flask==3.0.3`**: The web framework used to build the application.
*   **`itsdangerous==2.2.0`**: A utility library used by Flask for securely signing data, which is essential for things like session management.
*   **`Jinja2==3.1.4`**: The templating engine used by Flask to render HTML pages dynamically.
*   **`Werkzeug==3.0.3`**: A comprehensive WSGI (Web Server Gateway Interface) toolkit that underlies Flask, providing utilities like request/response objects and password hashing.
*   **`python-dotenv==1.0.1`**: A library that loads environment variables from a `.env` file into `os.environ`, which is crucial for managing application configurations (like `SECRET_KEY` and email credentials) outside of the codebase.
*   **`requests==2.31.0`**: A popular and easy-to-use HTTP library for making web requests. This is used extensively, for example, in `utils.py` for geolocation APIs.

**🔄 Role in Overall Application Flow:**

The `requirements.txt` file is critical for setting up the development and deployment environment. It allows anyone to easily install all necessary dependencies using a command like `pip install -r requirements.txt`. This ensures that the application has all the required third-party libraries available in their specified versions, which are integral to the functionality of various modules, from the Flask web server itself to external API interactions and secure data handling.
