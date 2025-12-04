/**
 * Authentication UI Helpers
 * ==========================
 * Toast notifications, form validation, loading states
 */

// Toast Notification System
const Toast = {
    container: null,

    init() {
        this.container = document.getElementById('toastContainer');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toastContainer';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = document.createElement('div');
        icon.className = 'toast-icon';

        const content = document.createElement('div');
        content.className = 'toast-content';

        let title = '';
        switch (type) {
            case 'success':
                title = 'Success';
                break;
            case 'error':
                title = 'Error';
                break;
            case 'info':
                title = 'Info';
                break;
        }

        content.innerHTML = `
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        `;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '×';
        closeBtn.onclick = () => this.remove(toast);

        toast.appendChild(icon);
        toast.appendChild(content);
        toast.appendChild(closeBtn);

        this.container.appendChild(toast);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }

        return toast;
    },

    remove(toast) {
        if (toast && toast.parentNode) {
            toast.style.animation = 'toastSlideIn 0.3s reverse';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    },

    success(message, duration) {
        return this.show(message, 'success', duration);
    },

    error(message, duration) {
        return this.show(message, 'error', duration);
    },

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
};

// Form Validation
const FormValidator = {
    validateUsername(username) {
        if (!username || username.length < 3) {
            return { valid: false, message: 'Username must be at least 3 characters' };
        }
        if (username.length > 30) {
            return { valid: false, message: 'Username must be at most 30 characters' };
        }
        if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            return { valid: false, message: 'Username can only contain letters, numbers, and underscores' };
        }
        return { valid: true, message: 'Valid username' };
    },

    validatePassword(password) {
        if (!password || password.length < 4) {
            return { valid: false, message: 'Password must be at least 4 characters' };
        }
        if (password.length > 100) {
            return { valid: false, message: 'Password must be at most 100 characters' };
        }
        return { valid: true, message: 'Valid password' };
    },

    getPasswordStrength(password) {
        if (!password) return 0;
        let strength = 0;
        if (password.length >= 4) strength++;
        if (password.length >= 8) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        return Math.min(strength, 3); // 0-3 scale
    }
};

// Button Loading State
function setButtonLoading(button, loading) {
    if (!button) return;
    if (loading) {
        button.disabled = true;
        button.classList.add('loading');
    } else {
        button.disabled = false;
        button.classList.remove('loading');
    }
}

// Error Display
function showFormError(errorElementId, message) {
    const errorEl = document.getElementById(errorElementId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.hidden = false;
    }
}

function hideFormError(errorElementId) {
    const errorEl = document.getElementById(errorElementId);
    if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = '';
    }
}

// Export globally
window.Toast = Toast;
window.FormValidator = FormValidator;
window.setButtonLoading = setButtonLoading;
window.showFormError = showFormError;
window.hideFormError = hideFormError;

// Initialize on load
Toast.init();
