function toggleAdType() {
    const customAd = document.getElementById('custom_ad').checked;
    const imageAd = document.getElementById('image_ad').checked;

    const customSection = document.getElementById('customDesignSection');
    const imageSection = document.getElementById('imageUploadSection');

    if (customAd) {
        customSection.style.display = 'contents';
        imageSection.style.display = 'none';
        // Remove required attribute from image input
        document.getElementById('adImageFile').removeAttribute('required');
    } else if (imageAd) {
        customSection.style.display = 'none';
        imageSection.style.display = 'block';
        // Add required attribute to image input
        document.getElementById('adImageFile').setAttribute('required', 'required');
    }

    updatePreview();
}

function previewImage() {
    const file = document.getElementById('adImageFile').files[0];
    const preview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');

    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        preview.style.display = 'none';
    }
}

function updatePreview() {
    const customAd = document.getElementById('custom_ad').checked;

    if (!customAd) {
        // For image ads, show a simple text preview
        const title = document.getElementById('adTitle').value || 'Amazing Product Launch!';
        const description = document.getElementById('adDescription').value || 'Discover amazing features that will boost your productivity...';
        const ctaText = document.getElementById('ctaText').value || 'Try Now!';

        const preview = document.getElementById('adPreview');
        const previewContent = preview.querySelector('.ad-preview-content');

        preview.style.background = 'linear-gradient(135deg, #6c757d 0%, #495057 100%)';
        preview.style.color = 'white';

        previewContent.innerHTML = `
      <div class="d-flex align-items-center mb-2">
        <i class="bi bi-image preview-icon me-2"></i>
        <h6 class="preview-title mb-0">${title}</h6>
      </div>
      <p class="preview-description mb-3">${description}</p>
      <button class="btn btn-sm preview-cta">${ctaText}</button>
      <div class="mt-2">
        <small style="opacity: 0.7;">
          <i class="bi bi-info-circle me-1"></i>Image will be displayed when uploaded
        </small>
      </div>
    `;
        return;
    }

    // Original custom ad preview logic
    const title = document.getElementById('adTitle').value || 'Amazing Product Launch!';
    const description = document.getElementById('adDescription').value || 'Discover amazing features that will boost your productivity...';
    const ctaText = document.getElementById('ctaText').value || 'Try Now!';
    const bgColor = document.getElementById('bgColor').value;
    const textColor = document.getElementById('textColor').value;
    const icon = document.getElementById('adIcon').value;

    const preview = document.getElementById('adPreview');
    const previewContent = preview.querySelector('.ad-preview-content');

    preview.style.background = `linear-gradient(135deg, ${bgColor} 0%, ${adjustColor(bgColor, -20)} 100%)`;
    preview.style.color = textColor;

    previewContent.innerHTML = `
    <div class="d-flex align-items-center mb-2">
      <span class="preview-icon me-2">${icon}</span>
      <h6 class="preview-title mb-0">${title}</h6>
    </div>
    <p class="preview-description mb-3">${description}</p>
    <button class="btn btn-sm preview-cta">${ctaText}</button>
  `;

    // Update color text inputs
    document.getElementById('bgColorText').value = bgColor;
    document.getElementById('textColorText').value = textColor;
}

function syncColor(type) {
    if (type === 'bg') {
        const textValue = document.getElementById('bgColorText').value;
        document.getElementById('bgColor').value = textValue;
    } else {
        const textValue = document.getElementById('textColorText').value;
        document.getElementById('textColor').value = textValue;
    }
    updatePreview();
}

function adjustColor(color, amount) {
    const usePound = color[0] === '#';
    const col = usePound ? color.slice(1) : color;
    const num = parseInt(col, 16);
    let r = (num >> 16) + amount;
    let g = (num >> 8 & 0x00FF) + amount;
    let b = (num & 0x0000FF) + amount;
    r = r > 255 ? 255 : r < 0 ? 0 : r;
    g = g > 255 ? 255 : g < 0 ? 0 : g;
    b = b > 255 ? 255 : b < 0 ? 0 : b;
    return (usePound ? '#' : '') + (r << 16 | g << 8 | b).toString(16).padStart(6, '0');
}

function resetPreview() {
    setTimeout(() => {
        document.getElementById('custom_ad').checked = true;
        document.getElementById('bgColor').value = '#667eea';
        document.getElementById('textColor').value = '#ffffff';
        document.getElementById('adIcon').value = '🚀';
        toggleAdType();
        updatePreview();
    }, 100);
}

// Initialize preview
document.addEventListener('DOMContentLoaded', function () {
    toggleAdType();
    updatePreview();
});
