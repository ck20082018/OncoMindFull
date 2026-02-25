// Регистрация и drag-and-drop функциональность
// Используем API_CONFIG из config.js
const API_URL = API_CONFIG.BASE_URL;

document.addEventListener('DOMContentLoaded', function() {
    // Переключатель ролей
    const roleBtns = document.querySelectorAll('.role-btn');
    const roleInput = document.getElementById('role');
    const doctorFields = document.getElementById('doctorFields');
    const patientFields = document.getElementById('patientFields');
    const diplomaInput = document.getElementById('diplomaNumber');

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
            if (validateFile(file)) {
                uploadedFiles.push(file);
                addFileToList(file);
            } else {
                showMessage(`Файл "${file.name}" имеет неподдерживаемый формат`, 'error');
            }
        }
    }

    function validateFile(file) {
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        return allowedTypes.includes(file.type) || allowedExtensions.includes(extension);
    }

    function addFileToList(file) {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <i class="fas fa-file"></i>
            <span class="file-name">${file.name}</span>
            <span class="file-size">(${formatFileSize(file.size)})</span>
            <button type="button" class="file-remove" onclick="removeFile('${file.name}')">
                <i class="fas fa-times"></i>
            </button>
        `;
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

    // Валидация формы
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        formMessage.textContent = '';
        
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (password !== confirmPassword) {
            showMessage('Пароли не совпадают', 'error');
            return;
        }

        const role = roleInput.value;
        
        // Валидация диплома для врача
        if (role === 'doctor') {
            const diplomaNumber = diplomaInput.value;
            if (!/^\d{8}$/.test(diplomaNumber)) {
                showMessage('Номер диплома должен содержать ровно 8 цифр', 'error');
                return;
            }
        }

        // Подготовка данных
        const formData = new FormData();
        formData.append('role', role);
        formData.append('fullName', document.getElementById('fullName').value);
        formData.append('email', document.getElementById('email').value);
        formData.append('password', password);
        
        if (role === 'doctor') {
            formData.append('diplomaNumber', diplomaNumber);
            formData.append('specialization', document.getElementById('specialization').value);
            formData.append('clinic', document.getElementById('clinic').value);
        } else {
            formData.append('birthDate', document.getElementById('birthDate').value);
            formData.append('phone', document.getElementById('phone').value);
        }

        // Добавление файлов
        uploadedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch(`${API_URL}/api/register`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showMessage('Регистрация успешна! Ожидайте подтверждения.', 'success');
                form.reset();
                uploadedFiles = [];
                fileList.innerHTML = '';
            } else {
                showMessage(result.error || 'Ошибка регистрации', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showMessage('Ошибка соединения с сервером', 'error');
        }
    });

    function showMessage(text, type) {
        formMessage.textContent = text;
        formMessage.className = 'form-message ' + type;
    }
});
