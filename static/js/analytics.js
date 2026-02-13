function exportToExcel() {
    const exportBtn = document.getElementById('exportExcelBtn');
    const originalText = exportBtn.innerHTML;

    // Show loading state
    exportBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generating Excel...';
    exportBtn.disabled = true;

    // Trigger Excel download
    window.location.href = '/analytics-overview/export-excel';

    // Reset button after a short delay
    setTimeout(() => {
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
    }, 2000);
}

function deleteLink(linkId, linkCode, deleteBtn) {
    // Show confirmation dialog
    if (!confirm(`Are you sure you want to delete the link "${linkCode}"?\n\nThis action cannot be undone and will delete:\n• The smart link\n• All analytics data\n• All visitor history\n\nClick OK to confirm deletion.`)) {
        return;
    }

    // Show loading state
    const originalContent = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
    deleteBtn.disabled = true;

    // Send delete request
    fetch(`/delete-link/${linkId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showAlert('success', data.message);

                // Remove the row from table with animation
                const row = deleteBtn.closest('tr');
                row.style.transition = 'opacity 0.3s ease';
                row.style.opacity = '0';

                setTimeout(() => {
                    row.remove();

                    // Update serial numbers
                    updateSerialNumbers();

                    // Check if table is empty and show empty state
                    const tbody = document.querySelector('tbody');
                    if (tbody.children.length === 0) {
                        location.reload(); // Reload to show empty state
                    }
                }, 300);

            } else {
                // Show error message
                showAlert('danger', data.message);

                // Reset button
                deleteBtn.innerHTML = originalContent;
                deleteBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('danger', 'An error occurred while deleting the link. Please try again.');

            // Reset button
            deleteBtn.innerHTML = originalContent;
            deleteBtn.disabled = false;
        });
}

function updateSerialNumbers() {
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach((row, index) => {
        const serialCell = row.querySelector('td:first-child span');
        if (serialCell) {
            serialCell.textContent = index + 1;
        }
    });
}

function showAlert(type, message) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

    // Add to page
    document.body.appendChild(alertDiv);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function () {
    // Add event listeners for delete buttons
    document.addEventListener('click', function (e) {
        if (e.target.closest('.delete-link-btn')) {
            const deleteBtn = e.target.closest('.delete-link-btn');
            const linkId = deleteBtn.dataset.linkId;
            const linkCode = deleteBtn.dataset.linkCode;

            deleteLink(linkId, linkCode, deleteBtn);
        }

        // Add event listeners for edit buttons
        if (e.target.closest('.edit-link-btn')) {
            const editBtn = e.target.closest('.edit-link-btn');
            const linkId = editBtn.dataset.linkId;
            const linkCode = editBtn.dataset.linkCode;
            const primaryUrl = editBtn.dataset.primaryUrl;
            const returningUrl = editBtn.dataset.returningUrl;
            const ctaUrl = editBtn.dataset.ctaUrl;
            const behaviorRule = editBtn.dataset.behaviorRule;

            // Fill modal
            document.getElementById('editLinkId').value = linkId;
            document.getElementById('modalLinkCode').textContent = linkCode;
            document.getElementById('editPrimaryUrl').value = primaryUrl;
            document.getElementById('editReturningUrl').value = returningUrl;
            document.getElementById('editCtaUrl').value = ctaUrl;

            // Set behavior rule
            const ruleSelect = document.getElementById('editBehaviorRule');
            if (ruleSelect) {
                ruleSelect.value = behaviorRule;
                // Trigger change event to show/hide fields
                ruleSelect.dispatchEvent(new Event('change'));
            }

            // Show modal
            const editModal = new bootstrap.Modal(document.getElementById('editLinkModal'));
            editModal.show();
        }
    });

    // Handle Behavior Rule Change
    const ruleSelect = document.getElementById('editBehaviorRule');
    if (ruleSelect) {
        ruleSelect.addEventListener('change', function () {
            const rule = this.value;
            const progressiveFields = document.getElementById('progressiveFields');
            const passwordFields = document.getElementById('passwordFields');

            // Hide all first
            if (progressiveFields) progressiveFields.style.display = 'none';
            if (passwordFields) passwordFields.style.display = 'none';

            // Show relevant
            if (rule === 'progression' && progressiveFields) {
                progressiveFields.style.display = 'block';
            } else if (rule === 'password_protected' && passwordFields) {
                passwordFields.style.display = 'block';
            }
        });
    }

    // Handle save button click
    const saveBtn = document.getElementById('saveLinkBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            const linkId = document.getElementById('editLinkId').value;
            const primaryUrl = document.getElementById('editPrimaryUrl').value;
            const returningUrl = document.getElementById('editReturningUrl').value;
            const ctaUrl = document.getElementById('editCtaUrl').value;

            if (!primaryUrl) {
                showAlert('danger', 'Primary URL is required');
                return;
            }

            const behaviorRule = document.getElementById('editBehaviorRule').value;
            const password = document.getElementById('editPassword').value;

            // Validate progressive fields
            if (behaviorRule === 'progression') {
                if (!returningUrl || !ctaUrl) {
                    showAlert('danger', 'Returning URL and CTA URL are required for Progressive Redirect');
                    return;
                }
            }

            // Validate password for NEW password protection (if switching to it)
            // We can't easily check if it HAS a password already without more data, so we rely on user to enter it if needed.
            if (behaviorRule === 'password_protected') {
                // Ideally we'd validte if password is provided if it wasn't before, but backend handles update logic.
                // We'll trust the user to enter a password if they want to set/change it.
            }

            // Show loading state
            const originalContent = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';
            saveBtn.disabled = true;

            // Send update request
            fetch('/update-link', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: linkId,
                    primary_url: primaryUrl,
                    returning_url: returningUrl,
                    cta_url: ctaUrl,
                    behavior_rule: behaviorRule,
                    password: password
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('success', data.message);
                        // Reload after a short delay to show updated data
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        showAlert('danger', data.message);
                        saveBtn.innerHTML = originalContent;
                        saveBtn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('danger', 'An error occurred while updating the link');
                    saveBtn.innerHTML = originalContent;
                    saveBtn.disabled = false;
                });
        });
    }
});
