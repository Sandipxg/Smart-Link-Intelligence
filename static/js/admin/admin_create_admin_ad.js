document.addEventListener('DOMContentLoaded', function () {
    // Toggle between custom and image ad options
    document.querySelectorAll('input[name="ad_type"]').forEach(radio => {
        radio.addEventListener('change', function () {
            const customOptions = document.getElementById('customAdOptions');
            const imageOptions = document.getElementById('imageAdOptions');
            const adImageInput = document.getElementById('ad_image');

            if (this.value === 'custom') {
                if (customOptions) customOptions.style.display = 'block';
                if (imageOptions) imageOptions.style.display = 'none';
                if (adImageInput) adImageInput.required = false;
            } else {
                if (customOptions) customOptions.style.display = 'none';
                if (imageOptions) imageOptions.style.display = 'block';
                if (adImageInput) adImageInput.required = true;
            }
            updatePreview();
        });
    });

    // Live preview updates
    function updatePreview() {
        const titleInput = document.getElementById('title');
        const descInput = document.getElementById('description');
        const iconInput = document.getElementById('icon');
        const bgInput = document.getElementById('background_color');
        const textInput = document.getElementById('text_color');
        const ctaInput = document.getElementById('cta_text');

        const title = titleInput ? (titleInput.value || 'Your Ad Title') : 'Your Ad Title';
        const description = descInput ? (descInput.value || 'Your ad description will appear here') : 'Your ad description will appear here';
        const icon = iconInput ? (iconInput.value || '🚀') : '🚀';
        const backgroundColor = bgInput ? bgInput.value : '#667eea';
        const textColor = textInput ? textInput.value : '#ffffff';
        const ctaText = ctaInput ? (ctaInput.value || 'Click Here') : 'Click Here';

        const previewContent = document.getElementById('previewContent');
        const previewIcon = document.getElementById('previewIcon');
        const previewTitle = document.getElementById('previewTitle');
        const previewDescription = document.getElementById('previewDescription');
        const previewButton = document.getElementById('previewButton');

        // Update content
        if (previewIcon) previewIcon.textContent = icon;
        if (previewTitle) previewTitle.textContent = title;
        if (previewDescription) previewDescription.textContent = description;
        if (previewButton) previewButton.textContent = ctaText;

        // Update colors
        if (previewContent) {
            previewContent.style.background = backgroundColor;
            previewContent.style.color = textColor;
        }
    }

    // Add event listeners for live preview
    const inputs = ['title', 'description', 'icon', 'background_color', 'text_color', 'cta_text'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updatePreview);
    });

    // Form validation
    const adForm = document.getElementById('adForm');
    if (adForm) {
        adForm.addEventListener('submit', function (e) {
            const adTypeChecked = document.querySelector('input[name="ad_type"]:checked');
            const adType = adTypeChecked ? adTypeChecked.value : 'custom';
            const adImageInput = document.getElementById('ad_image');
            const imageFile = adImageInput ? adImageInput.files[0] : null;

            if (adType === 'image' && !imageFile) {
                e.preventDefault();
                alert('Please select an image file for image-type advertisements.');
                return false;
            }

            // Validate URL
            const urlInput = document.getElementById('cta_url');
            const url = urlInput ? urlInput.value : '';
            if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
                e.preventDefault();
                alert('Please enter a valid URL starting with http:// or https://');
                return false;
            }
        });
    }

    // Character counters
    function addCharacterCounter(inputId, maxLength) {
        const input = document.getElementById(inputId);
        if (!input) return;
        const helpText = input.nextElementSibling;
        if (!helpText) return;

        input.addEventListener('input', function () {
            const remaining = maxLength - this.value.length;
            helpText.textContent = `${remaining} characters remaining`;

            if (remaining < 0) {
                helpText.classList.add('text-danger');
            } else {
                helpText.classList.remove('text-danger');
            }
        });
    }

    // Add character counters
    addCharacterCounter('title', 100);
    addCharacterCounter('description', 200);
    addCharacterCounter('cta_text', 50);

    // Run initial preview update
    updatePreview();
});
