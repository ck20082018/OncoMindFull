/**
 * OncoMind Frontend - Основные скрипты
 * 
 * ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ:
 * - Добавлена функция escapeHtml для защиты от XSS
 * - Санитизация всего пользовательского ввода
 * - Безопасная вставка HTML
 */

// =============================================================================
// БЕЗОПАСНОСТЬ: Защита от XSS
// =============================================================================

/**
 * Экранирование HTML для защиты от XSS атак
 * @param {string} text - Текст для экранирования
 * @returns {string} - Безопасный текст
 */
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };
    return String(text).replace(/[&<>"'`=\/]/g, m => map[m]);
}

/**
 * Безопасная вставка текста в элемент
 * @param {string} selector - CSS селектор
 * @param {string} text - Текст для вставки
 */
function setSafeText(selector, text) {
    const element = document.querySelector(selector);
    if (element) {
        element.textContent = text;
    }
}

/**
 * Создание безопасного HTML элемента
 * @param {string} tag - Тег элемента
 * @param {object} attributes - Атрибуты
 * @param {string} text - Текст содержимого
 * @returns {HTMLElement} - Созданный элемент
 */
function createSafeElement(tag, attributes = {}, text = '') {
    const element = document.createElement(tag);
    
    for (const [key, value] of Object.entries(attributes)) {
        // Разрешаем только безопасные атрибуты
        const safeAttributes = ['class', 'id', 'data-', 'href', 'src', 'alt', 'title', 'type', 'placeholder', 'disabled'];
        const isSafe = safeAttributes.some(safe => key === safe || key.startsWith('data-'));
        
        if (isSafe) {
            // Для href и src проверяем протокол
            if (key === 'href' || key === 'src') {
                if (value.startsWith('javascript:') || value.startsWith('data:')) {
                    console.warn('Blocked potentially dangerous URL:', value);
                    continue;
                }
            }
            element.setAttribute(key, value);
        } else {
            console.warn('Blocked unsafe attribute:', key);
        }
    }
    
    // Текст вставляем через textContent для защиты от XSS
    if (text) {
        element.textContent = text;
    }
    
    return element;
}

// =============================================================================
// МОБИЛЬНОЕ МЕНЮ
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
    const burgerMenu = document.querySelector('.burger-menu');
    const navMenu = document.querySelector('.nav-menu');

    if (burgerMenu) {
        burgerMenu.addEventListener('click', function() {
            this.classList.toggle('active');
            navMenu.classList.toggle('active');

            // Блокировка прокрутки body при открытом меню
            if (navMenu.classList.contains('active')) {
                document.body.style.overflow = 'hidden';
            } else {
                document.body.style.overflow = '';
            }
        });
    }

    // Закрытие меню при клике на ссылку
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            burgerMenu.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Подсветка активной страницы в меню
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    navLinks.forEach(link => {
        const linkPage = link.getAttribute('href');
        if (linkPage === currentPage) {
            link.classList.add('active');
        }
    });
});

// =============================================================================
// УТИЛИТЫ
// =============================================================================

/**
 * Форматирование даты
 * @param {string} dateString - Дата в формате ISO
 * @returns {string} - Отформатированная дата
 */
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Проверка email
 * @param {string} email - Email для проверки
 * @returns {boolean} - Валидность email
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

/**
 * Проверка сложности пароля
 * @param {string} password - Пароль для проверки
 * @returns {object} - Результат проверки
 */
function checkPasswordStrength(password) {
    const result = {
        valid: false,
        errors: []
    };
    
    if (password.length < 8) {
        result.errors.push('Минимум 8 символов');
    }
    if (!/[A-Z]/.test(password)) {
        result.errors.push('Хотя бы одна заглавная буква');
    }
    if (!/[a-z]/.test(password)) {
        result.errors.push('Хотя бы одна строчная буква');
    }
    if (!/\d/.test(password)) {
        result.errors.push('Хотя бы одна цифра');
    }
    
    result.valid = result.errors.length === 0;
    return result;
}

/**
 * Отображение уведомления
 * @param {string} message - Сообщение
 * @param {string} type - Тип (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    // Удаляем существующие уведомления
    const existing = document.querySelector('.notification-toast');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    notification.className = `notification-toast notification-${type}`;
    notification.textContent = message;
    
    // Стили уведомления
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '15px 25px',
        borderRadius: '8px',
        color: '#fff',
        fontWeight: '500',
        zIndex: '10000',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        animation: 'slideIn 0.3s ease',
        maxWidth: '400px'
    });
    
    // Цвета для разных типов
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    document.body.appendChild(notification);
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

/**
 * API запрос с обработкой ошибок
 * @param {string} url - URL endpoint
 * @param {object} options - Опции fetch
 * @returns {Promise} - Результат запроса
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    // Добавляем CSRF токен если есть
    const csrfToken = localStorage.getItem('csrf_token');
    if (csrfToken) {
        defaultOptions.headers['X-CSRF-Token'] = csrfToken;
    }
    
    // Добавляем ID пользователя если есть
    const userId = localStorage.getItem('user_id');
    if (userId) {
        defaultOptions.headers['X-User-Id'] = userId;
    }
    
    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        // Обработка 429 Too Many Requests
        if (response.status === 429) {
            const data = await response.json();
            const retryAfter = data.retry_after || 60;
            showNotification(
                `Слишком много запросов. Попробуйте через ${retryAfter} сек.`,
                'warning'
            );
            throw new Error('Rate limit exceeded');
        }
        
        // Обработка ошибок авторизации
        if (response.status === 401) {
            showNotification('Требуется авторизация', 'error');
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 2000);
            throw new Error('Unauthorized');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Произошла ошибка');
        }
        
        return data;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// =============================================================================
// АНИМАЦИИ
// =============================================================================

// Добавляем CSS для анимаций уведомлений
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// =============================================================================
// ЛОКАЛЬНОЕ ХРАНИЛИЩЕ
// =============================================================================

/**
 * Безопасное сохранение данных в localStorage
 * @param {string} key - Ключ
 * @param {any} value - Значение
 */
function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error('Error saving to localStorage:', error);
    }
}

/**
 * Безопасное получение данных из localStorage
 * @param {string} key - Ключ
 * @param {any} defaultValue - Значение по умолчанию
 * @returns {any} - Значение
 */
function getFromStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.error('Error reading from localStorage:', error);
        return defaultValue;
    }
}

/**
 * Очистка данных пользователя
 */
function clearUserData() {
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_role');
    localStorage.removeItem('csrf_token');
    sessionStorage.clear();
}

// Экспорт функций для использования в других модулях
window.OncoMindUtils = {
    escapeHtml,
    setSafeText,
    createSafeElement,
    formatDate,
    isValidEmail,
    checkPasswordStrength,
    showNotification,
    apiRequest,
    saveToStorage,
    getFromStorage,
    clearUserData
};
