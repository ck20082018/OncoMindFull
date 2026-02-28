/**
 * register.js - Логика страницы регистрации
 * 
 * ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ:
 * - Валидация пароля на клиенте
 * - Санитизация данных перед отображением
 * - Проверка сложности пароля
 * - Защита от XSS
 */

// Используем API_CONFIG из config.js
const API_URL = API_CONFIG.BASE_URL;

document.addEventListener('DOMContentLoaded', function() {
    // Переключатель ролей
    const roleBtns = document.querySelectorAll('.role-btn');
    const roleInput = document.getElementById('role');
    const doctorFields = document.getElementById('doctorFields');
    const patientFields = document.getElementById('patientFields');
    const diplomaInput = document.getElementById('diplomaNumber');

    // Инициализация полей при загрузке
    if (roleInput.value === 'doctor') {
        doctorFields.style.display = 'block';
        patientFields.style.display = 'none';
        diplomaInput.required = true;
    } else {
        doctorFields.style.display = 'none';
        patientFields.style.display = 'block';
        diplomaInput.required = false;
    }

    roleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const role = this.dataset.role;

            roleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            roleInput.value = role;

            if (role === 'doctor') {
                doctorFields.style.display = 'block';
                patientFields.style.display = 'none';
                diplomaInput.required = true;
            } else {
                doctorFields.style.display = 'none';
                patientFields.style.display = 'block';
                diplomaInput.required = false;
            }
        });
    });

    // Drag-and-drop зона
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const form = document.getElementById('registrationForm');
    const formMessage = document.getElementById('formMessage');

    const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'image/jpeg',
        'image/png',
        'image/jpg'
    ];

    const allowedExtensions = ['.pdf', '.xlsx', '.txt', '.jpg', '.jpeg', '.png'];
    const maxFileSize = 10 * 1024 * 1024; // 10 MB
    let uploadedFiles = [];

    // Клик по dropzone открывает выбор файлов
    dropzone.addEventListener('click', function() {
        fileInput.click();
    });

    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });

    dropzone.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    function handleFiles(files) {
        for (let file of files) {
            const validation = validateFile(file);
            if (validation.valid) {
                uploadedFiles.push(file);
                addFileToList(file);
            } else {
                showNotification('error', `Файл "${file.name}": ${validation.error}`);
            }
        }
    }

    function validateFile(file) {
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        // Проверка размера
        if (file.size > maxFileSize) {
            return {
                valid: false,
                error: 'Превышен максимальный размер (10 MB)'
            };
        }
        
        // Проверка типа
        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(extension)) {
            return {
                valid: false,
                error: 'Неподдерживаемый формат файла'
            };
        }
        
        return { valid: true };
    }

    function addFileToList(file) {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        // БЕЗОПАСНОСТЬ: Используем textContent вместо innerHTML
        const icon = document.createElement('i');
        icon.className = 'fas fa-file';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'file-name';
        nameSpan.textContent = file.name;
        
        const sizeSpan = document.createElement('span');
        sizeSpan.className = 'file-size';
        sizeSpan.textContent = `(${formatFileSize(file.size)})`;
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'file-remove';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.onclick = function() { removeFile(file.name); };
        
        item.appendChild(icon);
        item.appendChild(nameSpan);
        item.appendChild(sizeSpan);
        item.appendChild(removeBtn);
        
        fileList.appendChild(item);
    }

    window.removeFile = function(fileName) {
        uploadedFiles = uploadedFiles.filter(f => f.name !== fileName);
        const items = fileList.querySelectorAll('.file-item');
        items.forEach(item => {
            if (item.querySelector('.file-name').textContent === fileName) {
                item.remove();
            }
        });
    };

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' Б';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КБ';
        return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
    }

    // Валидация формы в реальном времени
    const passwordInput = document.getElementById('password');
    const passwordStrength = document.getElementById('passwordStrength');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const result = OncoMindUtils.checkPasswordStrength(this.value);
            if (passwordStrength) {
                passwordStrength.innerHTML = result.errors.length > 0 
                    ? '<small style="color: #ef4444;">' + result.errors.join(', ') + '</small>'
                    : '<small style="color: #10b981;">✓ Надёжный пароль</small>';
            }
        });
    }

    // Обработка отправки формы
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        formMessage.textContent = '';

        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // Проверка совпадения паролей
        if (password !== confirmPassword) {
            showNotification('error', 'Пароли не совпадают');
            return;
        }

        // БЕЗОПАСНОСТЬ: Проверка сложности пароля
        const passwordResult = OncoMindUtils.checkPasswordStrength(password);
        if (!passwordResult.valid) {
            showNotification('error', 'Требования к паролю: ' + passwordResult.errors.join(', '));
            return;
        }

        const role = roleInput.value;
        let diplomaNumber = '';

        // Валидация диплома для врача
        if (role === 'doctor') {
            diplomaNumber = diplomaInput.value.trim();
            if (!/^\d{8}$/.test(diplomaNumber)) {
                showNotification('error', 'Номер диплома должен содержать ровно 8 цифр');
                return;
            }
        }

        // БЕЗОПАСНОСТЬ: Валидация email
        const email = document.getElementById('email').value.trim();
        if (!OncoMindUtils.isValidEmail(email)) {
            showNotification('error', 'Введите корректный email');
            return;
        }

        // Подготовка данных
        const formData = new FormData();
        formData.append('role', role);
        formData.append('full_name', document.getElementById('fullName').value.trim());
        formData.append('email', email);
        formData.append('password', password);

        if (role === 'doctor') {
            formData.append('diploma_number', diplomaNumber);
            formData.append('specialization', document.getElementById('specialization').value.trim());
            formData.append('clinic', document.getElementById('clinic').value.trim());
        } else {
            formData.append('birth_date', document.getElementById('birthDate').value);
            formData.append('phone', document.getElementById('phone').value.trim());
        }

        // Добавление файлов
        uploadedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Регистрация...';

            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                showNotification('success', 'Регистрация успешна! Перенаправление...');
                form.reset();
                uploadedFiles = [];
                fileList.innerHTML = '';
                if (passwordStrength) passwordStrength.innerHTML = '';
                
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1500);
            } else {
                showNotification('error', result.error || 'Ошибка регистрации');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showNotification('error', 'Ошибка соединения с сервером');
        } finally {
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Зарегистрироваться';
        }
    });
});
