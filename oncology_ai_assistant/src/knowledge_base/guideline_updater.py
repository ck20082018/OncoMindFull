"""
=============================================================================
GUIDELINE_UPDATER.PY - Обновление клинических рекомендаций
=============================================================================
Модуль для автоматического обновления базы знаний клинических рекомендаций:
- Проверка обновлений на сайте Минздрава РФ
- Загрузка новых версий документов
- Версионирование и архивирование старых версий
- Планирование автоматических обновлений
=============================================================================
"""

import logging
import json
import hashlib
import shutil
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("requests не установлен. Обновление не будет работать.")


logger = logging.getLogger(__name__)


@dataclass
class GuidelineVersion:
    """Версия клинической рекомендации."""
    id: str
    title: str
    version: str
    approval_date: str
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    is_current: bool = True
    downloaded_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'id': self.id,
            'title': self.title,
            'version': self.version,
            'approval_date': self.approval_date,
            'file_url': self.file_url,
            'file_path': self.file_path,
            'file_hash': self.file_hash,
            'is_current': self.is_current,
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None
        }


@dataclass
class UpdateCheckResult:
    """Результат проверки обновлений."""
    checked_at: datetime
    source: str
    updates_available: bool
    new_versions: List[GuidelineVersion] = field(default_factory=list)
    current_versions: List[GuidelineVersion] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            'checked_at': self.checked_at.isoformat(),
            'source': self.source,
            'updates_available': self.updates_available,
            'new_versions_count': len(self.new_versions),
            'new_versions': [v.to_dict() for v in self.new_versions],
            'current_versions_count': len(self.current_versions),
            'errors': self.errors
        }


class MinzdravScraper:
    """
    Скрапер для сайта клинических рекомендаций Минздрава РФ.
    
    https://cr.minzdrav.gov.ru
    """
    
    BASE_URL = "https://cr.minzdrav.gov.ru"
    SEARCH_URL = f"{BASE_URL}/reestri_kr"
    
    def __init__(self, timeout: int = 30):
        """
        Инициализация скрапера.
        
        Args:
            timeout: Таймаут запросов в секундах.
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests не установлен")
        
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_guidelines(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Поиск клинических рекомендаций.
        
        Args:
            query: Поисковый запрос.
            limit: Максимальное количество результатов.
            
        Returns:
            Список рекомендаций.
        """
        # Примечание: Это пример реализации
        # Реальный сайт может требовать авторизации или иметь API
        logger.info(f"Поиск рекомендаций: {query}")
        
        try:
            # Пример запроса (реальная реализация зависит от структуры сайта)
            response = self.session.get(
                self.SEARCH_URL,
                params={'q': query, 'limit': limit},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Парсинг HTML (требуется BeautifulSoup)
            # Это заглушка для примера
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []
    
    def get_guideline_details(self, guideline_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить детали рекомендации.
        
        Args:
            guideline_id: ID рекомендации.
            
        Returns:
            Детали или None.
        """
        url = f"{self.BASE_URL}/schema/{guideline_id}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()  # Если есть API
        except Exception as e:
            logger.error(f"Ошибка получения деталей: {e}")
            return None
    
    def download_guideline(
        self,
        guideline_id: str,
        save_path: Path
    ) -> Optional[Path]:
        """
        Скачать файл рекомендации.
        
        Args:
            guideline_id: ID рекомендации.
            save_path: Путь для сохранения.
            
        Returns:
            Путь к файлу или None.
        """
        url = f"{self.BASE_URL}/download/{guideline_id}"
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Скачано: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return None


class GuidelineUpdater:
    """
    Менеджер обновлений клинических рекомендаций.
    
    Использование:
        updater = GuidelineUpdater(data_dir="knowledge_base_data/minzdrav")
        result = updater.check_for_updates()
        if result.updates_available:
            updater.download_updates(result.new_versions)
    """
    
    def __init__(
        self,
        data_dir: str = "knowledge_base_data/minzdrav",
        archive_dir: Optional[str] = None,
        auto_backup: bool = True
    ):
        """
        Инициализация обновлятора.
        
        Args:
            data_dir: Директория с документами.
            archive_dir: Директория для архива старых версий.
            auto_backup: Автоматически создавать резервные копии.
        """
        self.data_dir = Path(data_dir)
        self.archive_dir = Path(archive_dir) if archive_dir else (self.data_dir / "archive")
        self.auto_backup = auto_backup
        
        self.scraper: Optional[MinzdravScraper] = None
        
        # Создаём директории
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.auto_backup:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Состояние версий
        self._versions_file = self.data_dir / "versions.json"
        self._versions: Dict[str, GuidelineVersion] = {}
        
        self._load_versions()
        
        logger.info(f"GuidelineUpdater инициализирован: {self.data_dir}")
    
    def _load_versions(self) -> None:
        """Загрузить информацию о версиях."""
        if self._versions_file.exists():
            try:
                with open(self._versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._versions = {
                    k: GuidelineVersion(**v)
                    for k, v in data.items()
                }
                logger.info(f"Загружено {len(self._versions)} версий")
            except Exception as e:
                logger.error(f"Ошибка загрузки версий: {e}")
    
    def _save_versions(self) -> None:
        """Сохранить информацию о версиях."""
        try:
            with open(self._versions_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._versions.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Ошибка сохранения версий: {e}")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Вычислить хэш файла."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def check_for_updates(self) -> UpdateCheckResult:
        """
        Проверить наличие обновлений.
        
        Returns:
            UpdateCheckResult.
        """
        logger.info("Проверка обновлений клинических рекомендаций")
        
        result = UpdateCheckResult(
            checked_at=datetime.now(),
            source="Минздрав РФ"
        )
        
        if not REQUESTS_AVAILABLE:
            result.errors.append("requests не установлен")
            return result
        
        # Инициализируем скрапер если нужно
        if self.scraper is None:
            self.scraper = MinzdravScraper()
        
        # Список онкологических рекомендаций для проверки
        oncology_queries = [
            "рак молочной железы",
            "рак лёгкого",
            "меланома",
            "лимфома",
            "лейкоз",
            "рак желудка",
            "рак кишечника",
            "рак простаты",
            "рак яичников",
            "рак шейки матки",
        ]
        
        # Проверяем каждую категорию
        for query in oncology_queries:
            try:
                guidelines = self.scraper.search_guidelines(query, limit=5)
                
                for gl in guidelines:
                    version = self._parse_guideline_version(gl)
                    if version:
                        existing = self._versions.get(version.id)
                        
                        if existing is None:
                            # Новая рекомендация
                            result.new_versions.append(version)
                        elif version.version != existing.version:
                            # Обновление
                            result.new_versions.append(version)
                            version.is_current = False
                        else:
                            result.current_versions.append(version)
                            
            except Exception as e:
                logger.error(f"Ошибка проверки '{query}': {e}")
                result.errors.append(str(e))
        
        result.updates_available = len(result.new_versions) > 0
        
        logger.info(
            f"Проверка завершена: {len(result.new_versions)} обновлений, "
            f"{len(result.current_versions)} актуальных"
        )
        
        return result
    
    def _parse_guideline_version(self, data: Dict[str, Any]) -> Optional[GuidelineVersion]:
        """Распарсить данные рекомендации в версию."""
        try:
            return GuidelineVersion(
                id=data.get('id', ''),
                title=data.get('title', ''),
                version=data.get('version', '1.0'),
                approval_date=data.get('approval_date', ''),
                file_url=data.get('file_url'),
                is_current=True
            )
        except Exception as e:
            logger.error(f"Ошибка парсинга версии: {e}")
            return None
    
    def download_updates(
        self,
        versions: List[GuidelineVersion],
        force: bool = False
    ) -> List[Path]:
        """
        Скачать обновления.
        
        Args:
            versions: Версии для скачивания.
            force: Скачивать даже если файл существует.
            
        Returns:
            Список скачанных файлов.
        """
        if self.scraper is None:
            self.scraper = MinzdravScraper()
        
        downloaded = []
        
        for version in versions:
            # Проверяем есть ли уже файл
            existing_path = self.data_dir / f"{version.id}.pdf"
            
            if existing_path.exists() and not force:
                logger.info(f"Файл уже существует: {existing_path}")
                
                # Проверяем хэш
                current_hash = self._compute_file_hash(existing_path)
                if current_hash == version.file_hash:
                    continue
            
            # Создаём временный файл для скачивания
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            try:
                # Скачиваем
                if version.file_url:
                    result_path = self.scraper.download_guideline(
                        version.id,
                        tmp_path
                    )
                    
                    if result_path:
                        # Вычисляем хэш
                        version.file_hash = self._compute_file_hash(tmp_path)
                        version.file_path = str(existing_path)
                        version.downloaded_at = datetime.now()
                        
                        # Архивируем старую версию если есть
                        if existing_path.exists() and self.auto_backup:
                            self._archive_file(existing_path)
                        
                        # Перемещаем в основную директорию
                        shutil.move(str(tmp_path), str(existing_path))
                        
                        # Обновляем информацию о версиях
                        self._versions[version.id] = version
                        self._save_versions()
                        
                        downloaded.append(existing_path)
                        logger.info(f"Скачано: {existing_path}")
                    else:
                        tmp_path.unlink(missing_ok=True)
                        
            except Exception as e:
                logger.error(f"Ошибка скачивания {version.id}: {e}")
                tmp_path.unlink(missing_ok=True)
        
        return downloaded
    
    def _archive_file(self, file_path: Path) -> None:
        """
        Архивировать файл.
        
        Args:
            file_path: Путь к файлу.
        """
        if not self.auto_backup:
            return
        
        archive_name = f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
        archive_path = self.archive_dir / archive_name
        
        shutil.copy2(file_path, archive_path)
        logger.info(f"Архивировано: {archive_path}")
    
    def list_current_versions(self) -> List[GuidelineVersion]:
        """Получить список текущих версий."""
        return [v for v in self._versions.values() if v.is_current]
    
    def get_version_history(self, guideline_id: str) -> List[GuidelineVersion]:
        """
        Получить историю версий рекомендации.
        
        Args:
            guideline_id: ID рекомендации.
            
        Returns:
            Список версий.
        """
        return [
            v for v in self._versions.values()
            if v.id == guideline_id
        ]
    
    def cleanup_old_archives(
        self,
        keep_days: int = 90
    ) -> int:
        """
        Очистить старые архивы.
        
        Args:
            keep_days: Хранить файлы новее N дней.
            
        Returns:
            Количество удалённых файлов.
        """
        if not self.archive_dir.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted = 0
        
        for file_path in self.archive_dir.glob("*.pdf"):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_date:
                file_path.unlink()
                deleted += 1
                logger.info(f"Удалён старый архив: {file_path}")
        
        logger.info(f"Очистка завершена: удалено {deleted} файлов")
        return deleted
    
    def export_versions_report(self, output_path: Optional[str] = None) -> Path:
        """
        Экспортировать отчёт о версиях.
        
        Args:
            output_path: Путь для отчёта.
            
        Returns:
            Путь к отчёту.
        """
        output = Path(output_path) if output_path else (self.data_dir / "versions_report.json")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_versions': len(self._versions),
            'current_versions': len([v for v in self._versions.values() if v.is_current]),
            'versions': {k: v.to_dict() for k, v in self._versions.items()}
        }
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчёт экспортирован: {output}")
        return output


# -----------------------------------------------------------------------------
# Утилитные функции
# -----------------------------------------------------------------------------

def check_updates(data_dir: str = "knowledge_base_data/minzdrav") -> UpdateCheckResult:
    """
    Проверить обновления.
    
    Args:
        data_dir: Директория с данными.
        
    Returns:
        UpdateCheckResult.
    """
    updater = GuidelineUpdater(data_dir=data_dir)
    return updater.check_for_updates()


def download_updates(data_dir: str = "knowledge_base_data/minzdrav") -> List[Path]:
    """
    Скачать доступные обновления.
    
    Args:
        data_dir: Директория с данными.
        
    Returns:
        Список скачанных файлов.
    """
    updater = GuidelineUpdater(data_dir=data_dir)
    result = updater.check_for_updates()
    
    if result.updates_available:
        return updater.download_updates(result.new_versions)
    
    return []
