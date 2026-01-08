// Initialize AOS
if (typeof AOS !== 'undefined') {
    AOS.init({
        duration: 800,
        easing: 'ease-in-out',
        once: true
    });
}

// Typewriter Animation
class TypewriterEffect {
    constructor(element, text, options = {}) {
        this.element = element;
        this.text = text;
        this.speed = options.speed || 100;
        this.delay = options.delay || 1000;
        this.cursor = document.getElementById('typewriter-cursor');
        this.currentIndex = 0;
        this.isComplete = false;

        // Start animation after a brief delay
        setTimeout(() => this.type(), this.delay);
    }

    type() {
        if (this.currentIndex < this.text.length) {
            // Get current character
            const currentChar = this.text.charAt(this.currentIndex);
            const currentText = this.text.substring(0, this.currentIndex + 1);

            // Update the text content
            if (this.element) this.element.innerHTML = this.formatText(currentText);

            this.currentIndex++;

            // Variable speed for more natural typing
            let nextDelay = this.speed;
            if (currentChar === ' ') {
                nextDelay = this.speed * 0.5; // Faster for spaces
            } else if (currentChar === ',' || currentChar === '.') {
                nextDelay = this.speed * 2; // Pause at punctuation
            }

            setTimeout(() => this.type(), nextDelay);
        } else {
            // Typing complete - hide cursor immediately
            this.isComplete = true;
            this.hideCursor();
        }
    }

    hideCursor() {
        if (this.cursor) {
            // Stop the blinking animation and hide cursor
            this.cursor.style.animation = 'none';
            this.cursor.style.opacity = '0';
            this.cursor.style.display = 'none';

            // Alternative method - remove the cursor element entirely
            setTimeout(() => {
                if (this.cursor && this.cursor.parentNode) {
                    this.cursor.parentNode.removeChild(this.cursor);
                }
            }, 300);
        }
    }

    formatText(text) {
        // Apply special styling to "Smart Links" while preserving cursor position
        let formattedText = text.replace(
            /Smart Links/g,
            '<span class="typewriter-word smart-links">Smart Links</span>'
        );

        return formattedText;
    }
}

// Initialize typewriter effect when page loads
document.addEventListener('DOMContentLoaded', function () {
    const typewriterElement = document.getElementById('typewriter-text');
    if (typewriterElement) {
        const text = "Intelligent Links with Behavioral AI & Analytics";
        new TypewriterEffect(typewriterElement, text, {
            speed: 75,  // Base typing speed in milliseconds
            delay: 800  // Initial delay before starting
        });
    }

    // Navbar scroll effect
    window.addEventListener('scroll', function () {
        const navbar = document.getElementById('navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    });

    // Counter animation
    function animateCounters() {
        const counters = document.querySelectorAll('[data-count]');
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-count'));
            const increment = target / 100;
            let current = 0;

            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    counter.textContent = target;
                    clearInterval(timer);
                } else {
                    counter.textContent = Math.floor(current);
                }
            }, 20);
        });
    }

    // Trigger counter animation when stats section is visible
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                observer.unobserve(entry.target);
            }
        });
    });

    const statsSection = document.querySelector('.stats-section');
    if (statsSection) {
        observer.observe(statsSection);
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;

            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Close mobile menu when clicking on a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                if (bsCollapse) bsCollapse.hide();
            }
        });
    });
});

// Video Modal
function openVideoModal() {
    const modal = document.getElementById('videoModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        // Stop video
        const iframe = modal.querySelector('iframe');
        if (iframe) {
            const src = iframe.src;
            iframe.src = '';
            iframe.src = src;
        }
    }
}

// Contact Form
function handleContactForm(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Sending...';
    submitBtn.disabled = true;
    
    // Get form data
    const formData = new FormData(form);
    
    // Submit to server
    fetch('/contact', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            alert(data.message);
            form.reset();
        } else {
            // Show error message
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while sending your message. Please try again later.');
    })
    .finally(() => {
        // Reset button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}
