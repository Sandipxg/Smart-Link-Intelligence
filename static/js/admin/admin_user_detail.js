let currentUserId = null;
let currentUsername = '';
let tierModal = null;

document.addEventListener('DOMContentLoaded', function () {
    const modalElement = document.getElementById('tierSelectionModal');
    if (modalElement) {
        tierModal = new bootstrap.Modal(modalElement);
    }
});

function deleteUser(userId, username) {
    if (confirm(`Are you sure you want to delete user "${username}"? This will permanently delete all their links, visits, and ads. This action cannot be undone.`)) {
        fetch(`/admin/users/${userId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    window.location.href = '/admin/users';
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error deleting user: ' + error);
            });
    }
}

function togglePremium(userId, username, currentStatus) {
    if (currentStatus) {
        // If already premium, confirm removal
        if (confirm(`Are you sure you want to REMOVE premium access for "${username}"?`)) {
            executePremiumToggle(userId, null);
        }
    } else {
        // If not premium, show tier selection modal
        currentUserId = userId;
        currentUsername = username;
        document.getElementById('modalUsername').textContent = username;
        if (tierModal) tierModal.show();
    }
}

function confirmPremiumGrant(tier) {
    if (confirm(`Are you sure you want to grant ${tier.replace('_', ' ')} access to "${currentUsername}"?`)) {
        executePremiumToggle(currentUserId, tier);
        if (tierModal) tierModal.hide();
    }
}

function executePremiumToggle(userId, tier) {
    fetch(`/admin/users/${userId}/toggle-premium`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tier: tier })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error toggling premium: ' + error);
        });
}

function toggleAd(adId) {
    fetch(`/admin/ads/${adId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error toggling ad: ' + error);
        });
}

function deleteAd(adId) {
    if (confirm('Are you sure you want to delete this ad?')) {
        fetch(`/admin/ads/${adId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error deleting ad: ' + error);
            });
    }
}
