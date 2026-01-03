document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form'); // Works for both login and signup as long as only one primary form exists
    const username = document.getElementById('username');
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirmPassword');
    const togglePassword = document.getElementById('togglePassword');
    const toggleIcon = document.getElementById('toggleIcon');
    const submitBtn = document.getElementById('submitBtn');
    const terms = document.getElementById('terms');

    // Password visibility toggle
    if (togglePassword && password && toggleIcon) {
        togglePassword.addEventListener('click', function () {
            const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
            password.setAttribute('type', type);
            toggleIcon.classList.toggle('bi-eye');
            toggleIcon.classList.toggle('bi-eye-slash');
        });
    }

    // Helper validation function
    function validateField(field, regex = null) {
        if (!field) return false;
        let isValid = false;
        if (regex) {
            isValid = regex.test(field.value);
        } else {
            isValid = field.value.trim().length > 0;
        }

        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
        }
        return isValid;
    }

    // --- Specific Logic for SIGNUP Page ---
    if (document.getElementById('signupForm')) {
        // Password strength checker
        function checkPasswordStrength(pw) {
            const requirements = {
                length: pw.length >= 8,
                uppercase: /[A-Z]/.test(pw),
                lowercase: /[a-z]/.test(pw),
                number: /\d/.test(pw),
                special: /[!@#$%^&*(),.?":{}|<>]/.test(pw)
            };

            // Update requirement indicators
            Object.keys(requirements).forEach(req => {
                const element = document.getElementById(req);
                if (element) {
                    const icon = element.querySelector('i');
                    if (requirements[req]) {
                        icon.className = 'bi bi-check-circle text-success me-1';
                        element.classList.remove('text-muted');
                        element.classList.add('text-success');
                    } else {
                        icon.className = 'bi bi-x-circle text-danger me-1';
                        element.classList.remove('text-success');
                        element.classList.add('text-muted');
                    }
                }
            });

            // Calculate strength
            const score = Object.values(requirements).filter(Boolean).length;
            const percentage = (score / 5) * 100;
            const strengthBar = document.getElementById('passwordStrength');
            const strengthText = document.getElementById('strengthText');

            if (strengthBar && strengthText) {
                strengthBar.style.width = percentage + '%';

                if (score < 2) {
                    strengthBar.className = 'progress-bar bg-danger';
                    strengthText.textContent = 'Weak password';
                } else if (score < 4) {
                    strengthBar.className = 'progress-bar bg-warning';
                    strengthText.textContent = 'Medium password';
                } else if (score < 5) {
                    strengthBar.className = 'progress-bar bg-info';
                    strengthText.textContent = 'Good password';
                } else {
                    strengthBar.className = 'progress-bar bg-success';
                    strengthText.textContent = 'Strong password';
                }
            }

            return score === 5;
        }

        // Listeners
        if (password) {
            password.addEventListener('input', function () {
                const strengthValid = checkPasswordStrength(this.value);
                if (strengthValid) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        }

        if (confirmPassword) {
            confirmPassword.addEventListener('input', function () {
                const isValid = this.value === password.value && this.value.length > 0;
                if (isValid) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        }

        if (username) {
            username.addEventListener('input', function () {
                validateField(this, /^[a-zA-Z0-9_]{3,20}$/);
            });
        }

        if (email) {
            email.addEventListener('input', function () {
                validateField(this, /^[^\s@]+@[^\s@]+\.[^\s@]+$/);
            });
        }

        // Submission
        form.addEventListener('submit', function (event) {
            const isUsernameValid = validateField(username, /^[a-zA-Z0-9_]{3,20}$/);
            const isEmailValid = validateField(email, /^[^\s@]+@[^\s@]+\.[^\s@]+$/);
            const isPasswordValid = checkPasswordStrength(password.value);
            const isConfirmPasswordValid = (confirmPassword.value === password.value && confirmPassword.value.length > 0);

            let isTermsAccepted = true;
            if (terms) {
                isTermsAccepted = terms.checked;
                if (!isTermsAccepted) {
                    terms.classList.add('is-invalid');
                    terms.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    terms.classList.remove('is-invalid');
                }
            }

            if (!isTermsAccepted || !isUsernameValid || !isEmailValid || !isPasswordValid || !isConfirmPasswordValid) {
                event.preventDefault();
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstInvalid.focus();
                }
                return false;
            }

            // Show loading state
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Creating Account...';
                submitBtn.disabled = true;
            }
            return true;
        });

    }
    // --- Specific Logic for LOGIN Page ---
    else if (document.getElementById('loginForm')) {
        if (username) {
            username.addEventListener('input', function () {
                validateField(this);
            });
        }
        if (password) {
            password.addEventListener('input', function () {
                validateField(this);
            });
        }

        form.addEventListener('submit', function (event) {
            // In login, we just want non-empty
            const isUsernameValid = validateField(username);
            const isPasswordValid = validateField(password);

            if (isUsernameValid && isPasswordValid) {
                if (submitBtn) {
                    // Show loading state
                    submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Signing In...';
                    submitBtn.disabled = true;
                }
                // Let default submit happen
            } else {
                event.preventDefault();
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });

        // Handle server-side errors passed via URL
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('error')) {
            if (username) username.classList.add('is-invalid');
            if (password) password.classList.add('is-invalid');
        }
    }
});
