document.addEventListener('DOMContentLoaded', function () {
    const audienceSelect = document.getElementById('audienceSelect');
    const multiUserContainer = document.getElementById('multiUserContainer');
    const userSearchInput = document.getElementById('userSearch');
    const userItems = document.querySelectorAll('.user-item');
    const userCheckboxes = document.querySelectorAll('.user-cb');
    const selectedCountSpan = document.getElementById('selectedCount');
    const clearSelectionBtn = document.getElementById('clearSelection');
    const noResults = document.getElementById('noResults');

    // Update selected count
    function updateCount() {
        const count = document.querySelectorAll('.user-cb:checked').length;
        if (selectedCountSpan) selectedCountSpan.textContent = count;
    }

    // Toggle container
    if (audienceSelect) {
        audienceSelect.addEventListener('change', function () {
            if (this.value === 'selected') {
                multiUserContainer.style.display = 'block';
            } else {
                multiUserContainer.style.display = 'none';
            }
        });
    }

    // Handle search
    if (userSearchInput) {
        userSearchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase();
            let visibleCount = 0;

            userItems.forEach(item => {
                const username = item.getAttribute('data-username');
                if (username.includes(query)) {
                    item.style.setProperty('display', '', 'important');
                    visibleCount++;
                } else {
                    item.style.setProperty('display', 'none', 'important');
                }
            });

            if (noResults) noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        });
    }

    // Handle selection changes
    userCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateCount);
    });

    // Clear all selection
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', function () {
            userCheckboxes.forEach(cb => {
                cb.checked = false;
            });
            updateCount();
        });
    }

    // Initial check
    if (audienceSelect && audienceSelect.value === 'selected') {
        if (multiUserContainer) multiUserContainer.style.display = 'block';
    }
    updateCount();
});
