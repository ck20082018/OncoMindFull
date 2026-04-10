// =============================================================================
// OncoMind - Конфигурация API
// =============================================================================
// Автоматическое определение окружения

const isLocalhost = window.location.hostname === 'localhost' ||
                    window.location.hostname === '127.0.0.1' ||
                    window.location.hostname === '';

// Production URL - ваш сервер
const PRODUCTION_URL = 'https://oncomind.ru';

// Local URL - для разработки (пустая строка = относительный URL через nginx)
const LOCAL_URL = '';

const API_CONFIG = {
    // Для локальной разработки - используем относительный URL (nginx проксирует /api/*)
    // Для продакшена - используем production URL
    BASE_URL: isLocalhost ? LOCAL_URL : PRODUCTION_URL,
    TIMEOUT: 30000
};

// Экспорт для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}

// Логирование для отладки
console.log('[API_CONFIG] Текущий URL:', API_CONFIG.BASE_URL, '(Localhost:', isLocalhost, ')');
