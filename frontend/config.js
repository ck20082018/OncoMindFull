// =============================================================================
// OncoMind - Конфигурация API
// =============================================================================
// Автоматическое определение окружения

const isLocalhost = window.location.hostname === 'localhost' ||
                    window.location.hostname === '127.0.0.1';

// Production URL - ваш сервер
const PRODUCTION_URL = 'https://155.212.182.149';

const API_CONFIG = {
    // Для локальной разработки (Live Server)
    BASE_URL: isLocalhost ? 'http://127.0.0.1:5000' : PRODUCTION_URL,
    TIMEOUT: 30000
};

// Экспорт для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}
