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
                    location.reload();
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
    const action = currentStatus ? 'remove' : 'grant';
    if (confirm(`Are you sure you want to ${action} premium access for "${username}"?`)) {
        fetch(`/admin/users/${userId}/toggle-premium`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
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
}
