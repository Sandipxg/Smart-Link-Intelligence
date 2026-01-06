// Real-time dashboard updates using AJAX polling
let updateInterval;
let isUpdating = false;

function updateLiveStats() {
    if (isUpdating) return; // Prevent concurrent updates
    isUpdating = true;

    fetch('/admin/api/stats/live')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const stats = data.stats;

                // Update stat cards with smooth animation
                updateStatCard('total_users', stats.total_users);
                updateStatCard('total_revenue', '$' + stats.total_revenue.toFixed(2));
                updateStatCard('total_links', stats.total_links);
                updateStatCard('active_ads', stats.active_ads);
                updateStatCard('recent_users', stats.recent_users);
                updateStatCard('total_visits', stats.total_visits);
                updateStatCard('total_ads', stats.total_ads);

                // Update last refresh time
                const now = new Date();
                const timeStr = now.toLocaleTimeString();
                updateLastRefresh(timeStr);
            }
        })
        .catch(error => {
            console.error('Error updating stats:', error);
        })
        .finally(() => {
            isUpdating = false;
        });
}

function updateStatCard(id, value) {
    const elements = document.querySelectorAll(`[data-stat="${id}"]`);
    elements.forEach(element => {
        if (element.textContent !== value.toString()) {
            // Add pulse animation on change
            element.classList.add('stat-updated');
            element.textContent = value;
            setTimeout(() => {
                element.classList.remove('stat-updated');
            }, 1000);
        }
    });
}

function updateLastRefresh(timeStr) {
    let refreshElement = document.getElementById('last-refresh');
    if (!refreshElement) {
        // Create refresh indicator if it doesn't exist
        const container = document.querySelector('.container-fluid');
        if (container) {
            refreshElement = document.createElement('div');
            refreshElement.id = 'last-refresh';
            refreshElement.className = 'text-muted small text-end mt-2';
            refreshElement.innerHTML = '<i class="fas fa-sync-alt"></i> Last updated: <span id="refresh-time"></span>';
            container.insertBefore(refreshElement, container.firstChild);
        }
    }
    const timeElement = document.getElementById('refresh-time');
    if (timeElement) {
        timeElement.textContent = timeStr;
    }
}

// Start polling every 5 seconds
updateInterval = setInterval(updateLiveStats, 5000);

// Initial update after 2 seconds
setTimeout(updateLiveStats, 2000);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
