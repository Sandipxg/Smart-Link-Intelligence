document.addEventListener('DOMContentLoaded', function () {
    // Initialize form fields visibility on page load
    showHideFields();

    const form = document.getElementById('linkCreateForm');

    if (form) {
        form.addEventListener('submit', function (e) {
            const behaviorRule = document.getElementById('behaviorRule').value;

            if (behaviorRule === 'progression') {
                const returningUrl = document.querySelector('input[name="returning_url"]');
                const ctaUrl = document.querySelector('input[name="cta_url"]');

                if (!returningUrl.value.trim() || !ctaUrl.value.trim()) {
                    e.preventDefault();
                    alert('Please fill in both Returning URL and CTA URL for progressive redirect.');
                    return false;
                }
            } else if (behaviorRule === 'password_protected') {
                const password = document.querySelector('input[name="password"]');
                if (!password.value.trim()) {
                    e.preventDefault();
                    alert('Please enter a password for the protected link.');
                    return false;
                }
            }
        });
    }
});

// Simple function to show/hide fields based on dropdown selection
function showHideFields() {
    const behaviorRule = document.getElementById('behaviorRule').value;
    const progressiveFields = document.getElementById('progressiveFields');
    const passwordFields = document.getElementById('passwordFields');

    // Hide all fields first
    progressiveFields.style.display = 'none';
    if (passwordFields) {
        passwordFields.style.display = 'none';
    }

    // Show relevant fields
    if (behaviorRule === 'progression') {
        progressiveFields.style.display = 'block';
    } else if (behaviorRule === 'password_protected') {
        passwordFields.style.display = 'block';
    }
}

function resetForm() {
    document.getElementById('linkCreateForm').reset();
    showHideFields(); // Reset the form fields visibility
}
