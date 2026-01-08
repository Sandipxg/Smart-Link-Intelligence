// Modern Landing Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize AOS (Animate On Scroll)
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 100
        });
    }

    // Initialize navbar scroll effect
    initNavbarScroll();
    
    // Initialize hero chart
    initHeroChart();
    
    // Initialize smooth scrolling
    initSmoothScrolling();
    
    // Initialize mobile menu
    initMobileMenu();
    
    // Initialize tech effects
    initTechEffects();
    
    // Initialize parallax effects
    initParallaxEffects();
    
    // Initialize typing animation
    initTypingAnimation();
});

// Navbar scroll effect
function initNavbarScroll() {
    const navbar = document.getElementById('navbar');
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        // Hide/show navbar on scroll
        if (currentScrollY > lastScrollY && currentScrollY > 100) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollY = currentScrollY;
    });
}

// Hero chart initialization
function initHeroChart() {
    const canvas = document.getElementById('heroChart');
    if (!canvas || typeof Chart === 'undefined') return;
    
    const ctx = canvas.getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.3)');
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.05)');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Clicks',
                data: [1200, 1900, 3000, 2500, 2847, 3200],
                borderColor: '#2563eb',
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: '#2563eb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: false
                }
            },
            elements: {
                point: {
                    hoverRadius: 8
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Smooth scrolling for anchor links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Mobile menu functionality
function initMobileMenu() {
    const toggler = document.querySelector('.modern-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (toggler && navbarCollapse) {
        toggler.addEventListener('click', () => {
            navbarCollapse.classList.toggle('show');
            toggler.classList.toggle('active');
        });
        
        // Close menu when clicking on nav links
        document.querySelectorAll('.modern-nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navbarCollapse.classList.remove('show');
                toggler.classList.remove('active');
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!toggler.contains(e.target) && !navbarCollapse.contains(e.target)) {
                navbarCollapse.classList.remove('show');
                toggler.classList.remove('active');
            }
        });
    }
}

// Tech-themed interactive effects
function initTechEffects() {
    // Circuit pulse effect on hover
    document.querySelectorAll('.circuit').forEach(circuit => {
        circuit.addEventListener('mouseenter', function() {
            this.style.animationDuration = '2s';
            this.style.opacity = '0.9';
        });
        
        circuit.addEventListener('mouseleave', function() {
            this.style.animationDuration = '8s';
            this.style.opacity = '0.6';
        });
    });
    
    // Code block typing effect on scroll
    const codeBlocks = document.querySelectorAll('.code-block');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('typing-active');
            }
        });
    }, { threshold: 0.5 });
    
    codeBlocks.forEach(block => observer.observe(block));
    
    // Random particle generation
    setInterval(createRandomParticle, 3000);
    
    // Tech cursor effect
    initTechCursor();
}

// Create random tech particles
function createRandomParticle() {
    const particles = ['{ }', '< >', '01', 'AI', '∞', 'λ', '⚡', '🔗', '⟨⟩', 'fn', 'var', 'let'];
    const particle = document.createElement('div');
    particle.className = 'particle temp-particle';
    particle.textContent = particles[Math.floor(Math.random() * particles.length)];
    particle.style.left = Math.random() * 100 + '%';
    particle.style.top = '100%';
    particle.style.color = `rgba(${37 + Math.random() * 50}, ${99 + Math.random() * 50}, 235, ${0.3 + Math.random() * 0.4})`;
    particle.style.fontSize = (12 + Math.random() * 8) + 'px';
    particle.style.animation = `particleFloat ${10 + Math.random() * 10}s linear forwards`;
    
    document.querySelector('.tech-particles').appendChild(particle);
    
    // Remove after animation
    setTimeout(() => {
        if (particle.parentNode) {
            particle.parentNode.removeChild(particle);
        }
    }, 20000);
}

// Tech cursor effect
function initTechCursor() {
    const cursor = document.createElement('div');
    cursor.className = 'tech-cursor';
    cursor.innerHTML = '<div class="cursor-dot"></div><div class="cursor-ring"></div>';
    document.body.appendChild(cursor);
    
    let mouseX = 0, mouseY = 0;
    let cursorX = 0, cursorY = 0;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    function animateCursor() {
        cursorX += (mouseX - cursorX) * 0.1;
        cursorY += (mouseY - cursorY) * 0.1;
        cursor.style.transform = `translate(${cursorX}px, ${cursorY}px)`;
        requestAnimationFrame(animateCursor);
    }
    
    animateCursor();
    
    // Cursor interactions
    document.querySelectorAll('a, button, .feature-card, .pricing-card').forEach(el => {
        el.addEventListener('mouseenter', () => cursor.classList.add('cursor-hover'));
        el.addEventListener('mouseleave', () => cursor.classList.remove('cursor-hover'));
    });
}

// Parallax effects for tech elements
function initParallaxEffects() {
    const techElements = document.querySelectorAll('.circuit, .code-block, .particle');
    const streams = document.querySelectorAll('.stream');
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.3;
        
        // Parallax for circuits and code blocks
        techElements.forEach((element, index) => {
            const speed = (index % 3 + 1) * 0.1;
            element.style.transform = `translateY(${rate * speed}px) rotate(${scrolled * 0.01}deg)`;
        });
        
        // Special effect for data streams
        streams.forEach((stream, index) => {
            const speed = (index + 1) * 0.05;
            stream.style.transform = `translateY(${rate * speed}px)`;
        });
        
        // Grid animation based on scroll
        const gridLines = document.querySelector('.grid-lines');
        const gridDots = document.querySelector('.grid-dots');
        
        if (gridLines) {
            gridLines.style.transform = `translate(${scrolled * 0.1}px, ${scrolled * 0.1}px)`;
        }
        
        if (gridDots) {
            gridDots.style.transform = `translate(${-scrolled * 0.05}px, ${-scrolled * 0.05}px)`;
        }
    });
}

// Typing animation for hero title
function initTypingAnimation() {
    const heroTitle = document.querySelector('.hero-title');
    if (!heroTitle) return;
    
    const text = 'Transform Your Links Into Smart Experiences';
    const words = text.split(' ');
    let currentWordIndex = 0;
    let currentText = '';
    
    // Clear existing content
    heroTitle.innerHTML = '';
    
    function typeWord() {
        if (currentWordIndex < words.length) {
            const word = words[currentWordIndex];
            
            if (word === 'Smart') {
                currentText += `<span class="gradient-text">${word}</span> `;
            } else {
                currentText += word + ' ';
            }
            
            heroTitle.innerHTML = currentText + '<span class="typing-cursor">|</span>';
            currentWordIndex++;
            
            setTimeout(typeWord, 300);
        } else {
            // Remove cursor after typing is complete
            setTimeout(() => {
                heroTitle.innerHTML = currentText.trim();
            }, 1000);
        }
    }
    
    // Start typing animation after a delay
    setTimeout(typeWord, 1000);
}

// Demo modal functionality
function openDemoModal() {
    const modal = document.getElementById('demoModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeDemoModal() {
    const modal = document.getElementById('demoModal');
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

// Contact form handling
function handleContactForm(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = document.getElementById('submitBtn');
    const originalContent = submitBtn.innerHTML;
    
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
            // Show success message with animation
            showNotification('Thank you! Your message has been sent successfully.', 'success');
            form.reset();
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again later.', 'error');
    })
    .finally(() => {
        // Reset button state
        submitBtn.innerHTML = originalContent;
        submitBtn.disabled = false;
    });
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="bi bi-x"></i>
        </button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.9)'};
        color: white;
        padding: 16px 20px;
        border-radius: 12px;
        backdrop-filter: blur(20px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 12px;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        opacity: 0.8;
        transition: opacity 0.2s ease;
    }
    
    .notification-close:hover {
        opacity: 1;
        background: rgba(255, 255, 255, 0.1);
    }
    
    .typing-cursor {
        animation: blink 1s infinite;
        color: #2563eb;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
`;
document.head.appendChild(style);

// Intersection Observer for animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
        }
    });
}, observerOptions);

// Observe elements for animation
document.querySelectorAll('.feature-card, .pricing-card').forEach(el => {
    observer.observe(el);
});

// Add hover effects for interactive elements
document.querySelectorAll('.btn, .feature-card, .pricing-card').forEach(element => {
    element.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    element.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Performance optimization: Throttle scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Apply throttling to scroll events
window.addEventListener('scroll', throttle(() => {
    // Scroll-based animations can be added here
}, 16)); // ~60fps