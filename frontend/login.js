// login.js - Логика страницы входа
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

            // Валидация
            if (!email || !password) {
                showMessage('error', 'Заполните все поля');
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
                    showMessage('success', 'Вход выполнен! Перенаправление...');
                    
                    // Сохраняем данные пользователя
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    if (remember) {
                        localStorage.setItem('rememberedEmail', email);
                    } else {
                        localStorage.removeItem('rememberedEmail');
                    }
                    
                    // Перенаправление в зависимости от роли
                    setTimeout(() => {
                        if (data.user.role === 'doctor') {
                            window.location.href = 'doctor-dashboard.html'; // Создадим позже
                        } else {
                            window.location.href = 'patient-dashboard.html'; // Создадим позже
                        }
                    }, 1500);
                    
                } else {
                    // Ошибка входа
                    showMessage('error', data.error || 'Ошибка входа');
                }
                
            } catch (error) {
                console.error('Ошибка:', error);
                showMessage('error', 'Ошибка подключения к серверу. Убедитесь, что бэкенд запущен (python app.py)');
            } finally {
                // Возвращаем кнопку в исходное состояние
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
    
    // Функция показа сообщений
    function showMessage(type, text) {
        if (!formMessage) return;
        
        formMessage.textContent = text;
        formMessage.className = 'form-message ' + type;
        formMessage.style.display = 'block';
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            formMessage.style.display = 'none';
        }, 5000);
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
        localStorage.removeItem('user');
        showMessage('success', 'Вы вышли из системы');
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