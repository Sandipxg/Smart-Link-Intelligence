document.addEventListener('DOMContentLoaded', function () {
    // Update preview when values change
    const returningWindow = document.querySelector('input[name="returning_window_hours"]');
    const interestedThreshold = document.querySelector('input[name="interested_threshold"]');
    const engagedThreshold = document.querySelector('input[name="engaged_threshold"]');

    function updatePreview() {
        const hours = returningWindow.value;
        const interested = interestedThreshold.value;
        const engaged = engagedThreshold.value;

        document.getElementById('interestedPreview').textContent = `${interested}+ visits in ${hours}h`;
        document.getElementById('engagedPreview').textContent = `${engaged}+ clicks total`;
    }

    if (returningWindow && interestedThreshold && engagedThreshold) {
        returningWindow.addEventListener('input', updatePreview);
        interestedThreshold.addEventListener('input', updatePreview);
        engagedThreshold.addEventListener('input', updatePreview);
    }
});
