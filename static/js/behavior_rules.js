document.addEventListener('DOMContentLoaded', function () {
    // Update preview for Create Modal
    const returningWindow = document.querySelector('#createRuleModal input[name="returning_window_hours"]');
    const interestedThreshold = document.querySelector('#createRuleModal input[name="interested_threshold"]');
    const engagedThreshold = document.querySelector('#createRuleModal input[name="engaged_threshold"]');

    function updatePreview() {
        if (!returningWindow) return;
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

    // Edit Rule Modal Population
    const editRuleModal = document.getElementById('editRuleModal');
    if (editRuleModal) {
        editRuleModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;

            // Extract info from data- attributes
            const ruleId = button.getAttribute('data-rule-id');
            const ruleName = button.getAttribute('data-rule-name');
            const returningWindow = button.getAttribute('data-returning-window');
            const interested = button.getAttribute('data-interested');
            const engaged = button.getAttribute('data-engaged');

            // Find modal inputs
            const form = document.getElementById('editRuleForm');

            // Update form action
            form.action = `/behavior-rules/update/${ruleId}`;

            // Fill inputs
            document.getElementById('edit_rule_name').value = ruleName;
            document.getElementById('edit_returning_window').value = returningWindow;
            document.getElementById('edit_interested').value = interested;
            document.getElementById('edit_engaged').value = engaged;
        });
    }
});
