(function() {
    'use strict';

    function showMessage(message, type) {
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const mainContent = document.querySelector('main') || document.querySelector('.container');
        if (mainContent) {
            mainContent.insertBefore(alertDiv, mainContent.firstChild);
        } else {
            document.body.insertBefore(alertDiv, document.body.firstChild);
        }

        setTimeout(() => {
            if (alertDiv.parentNode) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, 5000);
    }

    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function refreshCaptcha() {
        const captchaImg = document.getElementById('captchaImage');
        if (captchaImg) {
            fetch('/refresh-captcha')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        captchaImg.src = '/captcha?' + new Date().getTime();
                    }
                })
                .catch(error => {
                    console.error('刷新验证码失败:', error);
                    captchaImg.src = '/captcha?' + new Date().getTime();
                });
        }
    }

    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    function initializePopovers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    function countRemainingChars(textarea, maxLength) {
        const currentLength = textarea.value.length;
        const remaining = maxLength - currentLength;
        
        let counterElement = textarea.parentNode.querySelector('.char-counter');
        if (!counterElement) {
            counterElement = document.createElement('small');
            counterElement.className = 'char-counter text-muted';
            textarea.parentNode.appendChild(counterElement);
        }
        
        counterElement.textContent = `剩余 ${remaining} 个字符`;
        
        if (remaining < 0) {
            counterElement.classList.add('text-danger');
            counterElement.classList.remove('text-muted');
        } else {
            counterElement.classList.remove('text-danger');
            counterElement.classList.add('text-muted');
        }
    }

    function setupCharacterCounters() {
        const textareas = document.querySelectorAll('textarea[maxlength]');
        textareas.forEach(textarea => {
            const maxLength = parseInt(textarea.getAttribute('maxlength'));
            
            countRemainingChars(textarea, maxLength);
            
            textarea.addEventListener('input', function() {
                countRemainingChars(this, maxLength);
            });
        });
    }

    function setupAutoResizeTextareas() {
        const textareas = document.querySelectorAll('textarea.auto-resize');
        
        function resize() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        }
        
        textareas.forEach(textarea => {
            textarea.addEventListener('input', resize);
            resize.call(textarea);
        });
    }

    function setupConfirmDialogs() {
        const confirmElements = document.querySelectorAll('[data-confirm]');
        
        confirmElements.forEach(element => {
            element.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm') || '确定要执行此操作吗？';
                
                if (!confirm(message)) {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
            });
        });
    }

    function setupSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const targetId = this.getAttribute('href');
                if (targetId !== '#') {
                    e.preventDefault();
                    const targetElement = document.querySelector(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });
    }

    function setupFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                let isValid = true;
                const requiredFields = this.querySelectorAll('[required]');
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('is-invalid');
                        
                        field.addEventListener('input', function() {
                            this.classList.remove('is-invalid');
                        }, { once: true });
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                    showMessage('请填写所有必填项', 'warning');
                }
            });
        });
    }

    function setupNumberInputs() {
        const numberInputs = document.querySelectorAll('input[type="number"][data-min][data-max]');
        
        numberInputs.forEach(input => {
            const min = parseInt(input.getAttribute('data-min'));
            const max = parseInt(input.getAttribute('data-max'));
            
            input.addEventListener('change', function() {
                let value = parseInt(this.value) || 0;
                
                if (value < min) {
                    this.value = min;
                    showMessage(`最小值为 ${min}`, 'warning');
                } else if (value > max) {
                    this.value = max;
                    showMessage(`最大值为 ${max}`, 'warning');
                }
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        initializeTooltips();
        initializePopovers();
        setupCharacterCounters();
        setupAutoResizeTextareas();
        setupConfirmDialogs();
        setupSmoothScroll();
        setupFormValidation();
        setupNumberInputs();
        
        const fadeElements = document.querySelectorAll('.fade-in');
        fadeElements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            element.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        });
    });

    window.VotingSystem = {
        showMessage: showMessage,
        formatDate: formatDate,
        debounce: debounce,
        refreshCaptcha: refreshCaptcha
    };

})();
