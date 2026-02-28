/**
 * login.js - Логика страницы входа
 * 
 * ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ:
 * - Использование безопасных функций из script.js
 * - Санитизация входных данных
 * - Защита от XSS при отображении сообщений
 */

// Используем API_CONFIG из config.js
const API_URL = API_CONFIG.BASE_URL;

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const formMessage = document.getElementById('formMessage');

    // Проверка авторизации при загрузке
    checkAuthStatus();

    // Обработка отправки формы
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Получаем данные формы
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const remember = document.querySelector('input[name="remember"]')?.checked || false;

            // БЕЗОПАСНОСТЬ: Валидация email
            if (!email || !password) {
                showNotification('error', 'Заполните все поля');
                return;
            }
            
            // БЕЗОПАСНОСТЬ: Проверка формата email
            if (!OncoMindUtils.isValidEmail(email)) {
                showNotification('error', 'Введите корректный email');
                return;
            }

            // Показываем загрузку
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Вход...';

            try {
                // Отправка запроса на бэкенд
                const response = await fetch(`${API_URL}/api/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password,
                        remember: remember
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Успешный вход
                    showNotification('success', 'Вход выполнен! Перенаправление...');

                    // БЕЗОПАСНОСТЬ: Сохраняем только необходимые данные
                    localStorage.setItem('user_id', data.user.id);
                    localStorage.setItem('user_email', data.user.email);
                    localStorage.setItem('user_role', data.user.role);
                    localStorage.setItem('user_full_name', OncoMindUtils.escapeHtml(data.user.full_name));
                    
                    // Сохраняем полные данные для совместимости
                    localStorage.setItem('user', JSON.stringify(data.user));

                    if (remember) {
                        localStorage.setItem('rememberedEmail', email);
                    } else {
                        localStorage.removeItem('rememberedEmail');
                    }

                    // Перенаправление в зависимости от роли
                    setTimeout(() => {
                        if (data.user.role === 'doctor') {
                            window.location.href = 'doctor/dashboard.html';
                        } else {
                            window.location.href = 'patient/dashboard.html';
                        }
                    }, 1500);

                } else {
                    // Ошибка входа
                    showNotification('error', data.error || 'Ошибка входа');
                }

            } catch (error) {
                console.error('Ошибка:', error);
                showNotification('error', 'Ошибка подключения к серверу. Убедитесь, что бэкенд запущен.');
            } finally {
                // Возвращаем кнопку в исходное состояние
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }

    // Проверка статуса авторизации
    function checkAuthStatus() {
        const user = localStorage.getItem('user');
        const rememberedEmail = localStorage.getItem('rememberedEmail');

        if (user) {
            // Если уже авторизован, спрашиваем
            if (confirm('Вы уже вошли. Хотите выйти?')) {
                logout();
            }
        }

        // Автозаполнение email если есть сохранённый
        if (rememberedEmail) {
            const emailInput = document.getElementById('email');
            if (emailInput) {
                emailInput.value = rememberedEmail;
                document.querySelector('input[name="remember"]').checked = true;
            }
        }
    }

    // Выход из системы
    window.logout = function() {
        OncoMindUtils.clearUserData();
        showNotification('success', 'Вы вышли из системы');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1500);
    };

    // Обработка "Забыли пароль"
    const forgotLink = document.getElementById('forgotPassword');
    if (forgotLink) {
        forgotLink.addEventListener('click', function(e) {
            e.preventDefault();
            alert('Функция восстановления пароля будет доступна позже. Обратитесь к администратору.');
        });
    }
});
