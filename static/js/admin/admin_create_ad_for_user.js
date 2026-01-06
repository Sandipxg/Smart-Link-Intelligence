// Live preview functionality
document.addEventListener('DOMContentLoaded', function () {
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const ctaInput = document.getElementById('cta_text');
    const backgroundInput = document.getElementById('background_color');
    const textColorInput = document.getElementById('text_color');
    const iconInput = document.getElementById('icon');

    const previewTitle = document.getElementById('preview-title');
    const previewDescription = document.getElementById('preview-description');
    const previewCta = document.getElementById('preview-cta');
    const previewIcon = document.getElementById('preview-icon');
    const previewContainer = document.getElementById('ad-preview');

    function updatePreview() {
        if (previewTitle) previewTitle.textContent = titleInput.value || 'Your Ad Title';
        if (previewDescription) previewDescription.textContent = descriptionInput.value || 'Your ad description will appear here';
        if (previewCta) previewCta.textContent = ctaInput.value || 'Call to Action';
        if (previewIcon) previewIcon.textContent = iconInput.value || '🚀';
        if (previewContainer) {
            previewContainer.style.background = backgroundInput.value;
            previewContainer.style.color = textColorInput.value;
        }
    }

    // Add event listeners
    if (titleInput) titleInput.addEventListener('input', updatePreview);
    if (descriptionInput) descriptionInput.addEventListener('input', updatePreview);
    if (ctaInput) ctaInput.addEventListener('input', updatePreview);
    if (backgroundInput) backgroundInput.addEventListener('input', updatePreview);
    if (textColorInput) textColorInput.addEventListener('input', updatePreview);
    if (iconInput) iconInput.addEventListener('input', updatePreview);

    // Initial update
    updatePreview();
});
