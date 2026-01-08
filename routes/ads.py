"""
Smart Link Intelligence - Advertisement Routes
Ad creation, management, and file uploads
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, g, current_app
from decorators import login_required
from database import query_db, execute_db
from config import MEMBERSHIP_TIERS

ads_bp = Blueprint('ads', __name__)


@ads_bp.route("/create-ad")
@login_required
def create_ad():
    """Create ad page"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check Membership
    user_dict = dict(g.user) if g.user else {}
    user_tier = user_dict.get("membership_tier", "free")
    if not user_tier: 
        user_tier = "free"
    
    if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["custom_ads"]:
        flash("Custom Ads are exclusive to Elite Pro members. Please upgrade to access this feature.", "warning")
        return redirect(url_for("main.index"))

    # Get user's existing ads
    user_ads = query_db(
        "SELECT * FROM personalized_ads WHERE user_id = ? ORDER BY created_at DESC",
        [g.user["id"]]
    )
    
    # Get ad statistics
    total_ads = len(user_ads)
    active_ads = len([ad for ad in user_ads if ad["is_active"]])
    
    # Track ad management view
    track_user_activity(g.user["id"], "view_ads", "Viewed ad management")
    
    return render_template("create_ad.html", user_ads=user_ads, total_ads=total_ads, active_ads=active_ads)


@ads_bp.route("/create-ad/submit", methods=["POST"])
@login_required
def submit_ad():
    """Submit new ad"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check Membership
    user_dict = dict(g.user) if g.user else {}
    user_tier = user_dict.get("membership_tier", "free")
    if not user_tier: 
        user_tier = "free"
    
    if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["custom_ads"]:
        flash("Custom Ads are exclusive to Elite Pro members.", "danger")
        return redirect(url_for("main.index"))

    data = {k: (request.form.get(k) or "").strip() for k in request.form.keys()}
    
    ad_type = data.get("ad_type", "custom")
    title = data.get("title")
    description = data.get("description")
    cta_text = data.get("cta_text")
    cta_url = data.get("cta_url")
    grid_position = int(data.get("grid_position", "1"))
    
    if not all([title, description, cta_text, cta_url]):
        flash("Title, description, CTA text, and URL are required", "danger")
        return redirect(url_for("ads.create_ad"))
    
    # Validate URL
    if not cta_url.startswith(('http://', 'https://')):
        flash("Please enter a valid URL starting with http:// or https://", "danger")
        return redirect(url_for("ads.create_ad"))
    
    # Validate grid position
    if grid_position not in [1, 2, 3]:
        flash("Invalid grid position selected", "danger")
        return redirect(url_for("ads.create_ad"))
    
    image_filename = None
    background_color = "#667eea"
    text_color = "#ffffff"
    icon = "🚀"
    
    if ad_type == "image":
        # Handle image upload
        if 'ad_image' not in request.files:
            flash("Please select an image file", "danger")
            return redirect(url_for("ads.create_ad"))
        
        file = request.files['ad_image']
        if file.filename == '':
            flash("Please select an image file", "danger")
            return redirect(url_for("ads.create_ad"))
        
        # Process and save image with proper resizing/cropping
        image_filename = process_and_save_image(file, g.user["id"])
        if not image_filename:
            flash("Error processing image. Please try a different image.", "danger")
            return redirect(url_for("ads.create_ad"))
    else:
        # Handle custom ad
        background_color = data.get("background_color", "#667eea")
        text_color = data.get("text_color", "#ffffff")
        icon = data.get("icon", "🚀")
    
    execute_db(
        """
        INSERT INTO personalized_ads 
        (user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [g.user["id"], title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename]
    )
    
    track_user_activity(g.user["id"], "create_ad", f"Created personal ad: {title}")
    flash("🎉 Your personalized ad has been created successfully!", "success")
    return redirect(url_for("ads.create_ad"))


@ads_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@ads_bp.route("/toggle-ad/<int:ad_id>", methods=["POST"])
@login_required
def toggle_ad(ad_id):
    """Toggle ad active status"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if ad belongs to current user
    ad = query_db(
        "SELECT * FROM personalized_ads WHERE id = ? AND user_id = ?",
        [ad_id, g.user["id"]], one=True
    )
    
    if not ad:
        flash("Ad not found", "danger")
        return redirect(url_for("ads.create_ad"))
    
    new_status = 0 if ad["is_active"] else 1
    execute_db(
        "UPDATE personalized_ads SET is_active = ? WHERE id = ?",
        [new_status, ad_id]
    )
    
    status_text = "activated" if new_status else "deactivated"
    track_user_activity(g.user["id"], "toggle_ad", f"Toggled ad status: {ad['title']} ({status_text})")
    flash(f"Ad has been {status_text}", "success")
    return redirect(url_for("ads.create_ad"))


@ads_bp.route("/delete-ad/<int:ad_id>", methods=["POST"])
@login_required
def delete_ad(ad_id):
    """Delete an ad"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if ad belongs to current user
    ad = query_db(
        "SELECT * FROM personalized_ads WHERE id = ? AND user_id = ?",
        [ad_id, g.user["id"]], one=True
    )
    
    if not ad:
        flash("Ad not found", "danger")
        return redirect(url_for("ads.create_ad"))
    
    track_user_activity(g.user["id"], "delete_ad", f"Deleted personal ad: {ad['title']}")
    execute_db("DELETE FROM personalized_ads WHERE id = ?", [ad_id])
    flash("Ad has been deleted", "success")
    return redirect(url_for("ads.create_ad"))


def process_and_save_image(file, user_id):
    """Process and save uploaded image (simplified implementation)"""
    try:
        from werkzeug.utils import secure_filename
        import uuid
        import os
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Get upload folder from app config
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        return unique_filename
    except Exception as e:
        print(f"Error processing image: {e}")
        return None