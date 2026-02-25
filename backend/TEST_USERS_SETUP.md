# Инструкция по настройке тестовых аккаунтов на сервере

## Проблема
Тестовые аккаунты не работают - выдают ошибку подключения к серверу, хотя сайт работает.

## Причина
На сервере отсутствует или пуст файл `backend/data/users.json` с тестовыми пользователями.

## Решение

### Вариант 1: Быстрое исправление (рекомендуется)

Подключитесь к серверу по SSH и выполните команды:

```bash
# 1. Перейдите в директорию backend
cd /var/www/oncomind/backend

# 2. Запустите скрипт создания тестовых пользователей
python init_test_users.py

# 3. Проверьте, что файл создан
ls -la data/users.json

# 4. Перезапустите backend сервис
systemctl restart oncomind

# 5. Проверьте статус сервиса
systemctl status oncomind

# 6. Проверьте логи
journalctl -u oncomind -n 20 --no-pager
```

### Вариант 2: Через деплой скрипт

```bash
cd /var/www/oncomind

# Обновите файлы из репозитория
git pull origin main

# Запустите скрипт инициализации
cd backend
python init_test_users.py

# Перезапустите сервисы
systemctl restart oncomind
systemctl restart nginx
```

## Проверка работы

После выполнения команд проверьте работу тестовых аккаунтов:

### Врачи:
- **Email:** doctor@oncomind.ai  
  **Пароль:** Doctor123!

- **Email:** elena.doctor@oncomind.ai  
  **Пароль:** Elena2026!

### Пациенты:
- **Email:** maria.patient@example.com  
  **Пароль:** Maria2026!

- **Email:** ivan.patient@example.com  
  **Пароль:** Ivan2026!

- **Email:** anna.test@example.com  
  **Пароль:** Anna2026!

## Диагностика

Если аккаунты всё равно не работают:

```bash
# 1. Проверьте, запущен ли backend
systemctl status oncomind

# 2. Проверьте логи backend
journalctl -u oncomind -f

# 3. Проверьте, доступен ли API
curl https://oncomind.ru/api/users

# 4. Проверьте права на файл users.json
ls -la /var/www/oncomind/backend/data/users.json

# 5. Проверьте содержимое файла
cat /var/www/oncomind/backend/data/users.json
```

## Примечание

Скрипт `init_test_users.py` создаёт тестовых пользователей только если файл `users.json` не существует или пуст. Для сброса всех пользователей и создания новых используйте:

```bash
python init_test_users.py --reset
```
