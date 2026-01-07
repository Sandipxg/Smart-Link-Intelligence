// Function to show visitor details modal
function showVisitorModal(row) {
    if (typeof JSON === 'undefined' || !row.dataset.visitor) return;

    const visitor = JSON.parse(row.dataset.visitor);

    const setContent = (id, content) => {
        const el = document.getElementById(id);
        if (el) el.textContent = content || 'N/A';
    };

    setContent('modal-ip', visitor.ip_address);
    setContent('modal-country', visitor.country || 'Unknown');
    setContent('modal-city', visitor.city || 'Unknown');
    setContent('modal-browser', visitor.browser || 'Unknown');
    setContent('modal-useragent', visitor.user_agent || 'Unknown');
    setContent('modal-referrer', visitor.referrer || 'no referrer');
    setContent('modal-hostname', visitor.hostname || 'Unknown');
    setContent('modal-isp', visitor.isp || 'Unknown');
    setContent('modal-org', visitor.org || 'Unknown');
    setContent('modal-timezone', visitor.timezone || 'Unknown');
    setContent('modal-device', visitor.device || 'Unknown');
    setContent('modal-behavior', visitor.behavior || 'Unknown');
    let displayTime = visitor.timestamp || 'Unknown';
    if (displayTime !== 'Unknown') {
        try {
            const date = new Date(displayTime.replace(' ', 'T') + 'Z');
            if (!isNaN(date.getTime())) {
                displayTime = new Intl.DateTimeFormat(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit', second: '2-digit',
                    hour12: true
                }).format(date);
            }
        } catch (e) { }
    }
    setContent('modal-timestamp', displayTime);

    // Coordinates
    const coordsEl = document.getElementById('modal-coords');
    if (coordsEl) {
        if (visitor.latitude && visitor.longitude) {
            coordsEl.innerHTML =
                `${visitor.latitude}, ${visitor.longitude} 
                 <a href="https://www.google.com/maps?q=${visitor.latitude},${visitor.longitude}" target="_blank" class="ms-2 btn btn-sm btn-outline-primary">
                   View on Map
                 </a>`;
        } else {
            coordsEl.textContent = 'Not available';
        }
    }

    // Show the modal
    const modalElement = document.getElementById('visitorModal');
    if (modalElement && typeof bootstrap !== 'undefined') {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }
}
