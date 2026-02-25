// auth-check.js - Проверка авторизации для всех страниц
// Используется на всех страницах для отображения статуса пользователя

(function() {
    'use strict';

    // Проверка авторизации при загрузке страницы
    document.addEventListener('DOMContentLoaded', function() {
        checkAuth();
    });

    function checkAuth() {
        const user = localStorage.getItem('user');
        
        if (user) {
            try {
                const userData = JSON.parse(user);
                updateUserInterface(userData);
            } catch (e) {
                console.error('Ошибка чтения данных пользователя:', e);
                localStorage.removeItem('user');
            }
        }
    }

    function updateUserInterface(userData) {
        // Найти навигационное меню
        const navMenu = document.querySelector('.nav-menu');
        if (!navMenu) return;

        // Очистить текущее меню
        navMenu.innerHTML = '';

        // Общие ссылки для всех
        const commonLinks = [
            { href: 'index.html', text: 'Главная' },
            { href: 'team.html', text: 'О команде' },
            { href: 'solutions.html', text: 'Медицинские ИИ решения' }
        ];

        // Добавить общие ссылки
        commonLinks.forEach(link => {
            const a = document.createElement('a');
            a.href = link.href;
            a.className = 'nav-link';
            a.textContent = link.text;
            navMenu.appendChild(a);
        });

        // Добавить ссылку на кабинет в зависимости от роли
        if (userData.role === 'doctor') {
            const cabinetLink = document.createElement('a');
            cabinetLink.href = 'doctor/dashboard.html';
            cabinetLink.className = 'btn btn-nav';
            cabinetLink.innerHTML = '<i class="fas fa-user-md"></i> Кабинет врача';
            navMenu.appendChild(cabinetLink);

            const logoutLink = document.createElement('a');
            logoutLink.href = '#';
            logoutLink.className = 'btn btn-nav';
            logoutLink.style.marginLeft = '10px';
            logoutLink.innerHTML = '<i class="fas fa-sign-out-alt"></i> Выйти';
            logoutLink.onclick = function(e) {
                e.preventDefault();
                logout();
            };
            navMenu.appendChild(logoutLink);
        } else if (userData.role === 'patient') {
            const cabinetLink = document.createElement('a');
            cabinetLink.href = 'patient/dashboard.html';
            cabinetLink.className = 'btn btn-nav';
            cabinetLink.innerHTML = '<i class="fas fa-user"></i> Кабинет пациента';
            navMenu.appendChild(cabinetLink);

            const logoutLink = document.createElement('a');
            logoutLink.href = '#';
            logoutLink.className = 'btn btn-nav';
            logoutLink.style.marginLeft = '10px';
            logoutLink.innerHTML = '<i class="fas fa-sign-out-alt"></i> Выйти';
            logoutLink.onclick = function(e) {
                e.preventDefault();
                logout();
            };
            navMenu.appendChild(logoutLink);
        }
    }

    // Функция выхода
    window.logout = function() {
        if (confirm('Вы уверены, что хотите выйти?')) {
            localStorage.removeItem('user');
            window.location.reload();
        }
    };

    // Экспорт функции для использования в других скриптах
    window.isAuthenticated = function() {
        return !!localStorage.getItem('user');
    };

    window.getCurrentUser = function() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    };
})();
