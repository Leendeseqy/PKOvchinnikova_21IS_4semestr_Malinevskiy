"""
Модуль управления серверами мессенджера.
Отвечает за запуск, остановку, конфигурацию и пароли серверов.
"""

import json
import os
import subprocess
import sys
import time
import hashlib
import socket
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from models.server_info import ServerInfo

# Импортируем AuthManager для хэширования паролей
try:
    from auth_manager import get_auth_manager
except ImportError:
    # Fallback для прямой структуры
    from auth_manager import get_auth_manager

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Конфигурация сервера"""
    name: str                    # Имя сервера
    ip: str                      # IP адрес
    port: int                    # Порт
    description: str = ""        # Описание
    password_protected: bool = False  # Защищен паролем
    password_hash: Optional[str] = None  # Хэш пароля (SHA256)
    created_at: str = ""         # Время создания
    config_path: str = ""        # Путь к файлу конфигурации
    server_path: str = ""        # Путь к исполняемым файлам сервера
    broadcast_port: int = 37020  # Порт для broadcast
    max_users: int = 50          # Максимальное количество пользователей
    auto_start: bool = False     # Автозапуск с клиентом
    is_default: bool = False     # Сервер по умолчанию
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ServerConfig':
        """Создание из словаря"""
        return cls(**data)
    
    def verify_password(self, password: str) -> bool:
        """Проверка пароля"""
        if not self.password_protected or not self.password_hash:
            return True  # Пароль не требуется
        
        auth_manager = get_auth_manager()
        return auth_manager.verify_password_hash(password, self.password_hash)
    
    def set_password(self, password: str):
        """Установка пароля"""
        if not password:
            self.password_protected = False
            self.password_hash = None
            return
        
        auth_manager = get_auth_manager()
        self.password_hash = auth_manager.hash_password(password)
        self.password_protected = True


class ServerManager:
    """
    Менеджер серверов мессенджера.
    
    Отвечает за:
    1. Хранение конфигураций серверов
    2. Запуск и остановку серверов
    3. Проверку паролей
    4. Управление файлами конфигураций
    """
    
    def __init__(self, config_dir: str = None):
        """
        Инициализация менеджера серверов.
        
        Args:
            config_dir: Директория для хранения конфигураций серверов
        """
        if config_dir is None:
            from config import SERVERS_DIR
            config_dir = SERVERS_DIR
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True, parents=True)
        
        self.servers: Dict[str, ServerConfig] = {}  # name -> ServerConfig
        self.running_servers: Dict[str, subprocess.Popen] = {}  # name -> process
        self.server_processes: Dict[str, Dict] = {}  # Информация о процессах
        
        self.auth_manager = get_auth_manager()
        self._load_servers()
        logger.info(f"ServerManager инициализирован. Загружено серверов: {len(self.servers)}")
    
    def _load_servers(self):
        """Загрузка конфигураций серверов из файлов"""
        self.servers.clear()
        
        try:
            config_files = list(self.config_dir.glob("*.json"))
            logger.debug(f"Найдено файлов конфигурации: {len(config_files)}")
            
            for config_file in config_files:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    config = ServerConfig.from_dict(config_data)
                    config.config_path = str(config_file)
                    
                    # Проверяем обязательные поля
                    if not config.name or not config.ip or not config.port:
                        logger.warning(f"Пропускаем некорректную конфигурацию: {config_file}")
                        continue
                    
                    # Проверяем дублирование
                    if config.name in self.servers:
                        logger.warning(f"Дублирование имени сервера: {config.name}")
                        continue
                    
                    self.servers[config.name] = config
                    logger.debug(f"Загружен сервер: {config.name}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка чтения JSON файла {config_file}: {e}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки сервера из {config_file}: {e}")
        
        except Exception as e:
            logger.error(f"Ошибка загрузки серверов: {e}")
    
    def save_server_config(self, config: ServerConfig) -> bool:
        """
        Сохранение конфигурации сервера.
        
        Args:
            config: Конфигурация сервера
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Генерируем имя файла из имени сервера
            safe_name = "".join(c for c in config.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_name:
                safe_name = "server"
            
            filename = f"{safe_name.replace(' ', '_')}.json"
            config_path = self.config_dir / filename
            config.config_path = str(config_path)
            
            # Сохраняем конфигурацию (исключаем пароли из логов)
            config_dict = config.to_dict()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            # Обновляем кэш
            self.servers[config.name] = config
            logger.info(f"Конфигурация сервера сохранена: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации сервера {config.name}: {e}")
            return False
    
    def create_server(
        self,
        name: str,
        ip: str,
        port: int,
        description: str = "",
        password: Optional[str] = None,
        broadcast_port: int = 37020,
        max_users: int = 50,
        auto_start: bool = False
    ) -> Tuple[bool, str]:
        """
        Создание нового сервера.
        
        Args:
            name: Имя сервера
            ip: IP адрес
            port: Порт
            description: Описание
            password: Пароль (опционально)
            broadcast_port: Порт для broadcast
            max_users: Максимальное количество пользователей
            auto_start: Автозапуск
            
        Returns:
            (успех, сообщение)
        """
        try:
            # Проверка валидности данных
            if not name or not name.strip():
                return False, "Имя сервера не может быть пустым"
            
            if not ip:
                return False, "IP адрес не может быть пустым"
            
            if port < 1024 or port > 65535:
                return False, "Порт должен быть в диапазоне 1024-65535"
            
            # Проверка дублирования имени
            if name in self.servers:
                return False, f"Сервер с именем '{name}' уже существует"
            
            # Проверка доступности порта
            if not self._check_port_available(ip, port):
                return False, f"Порт {port} уже используется"
            
            # Хэширование пароля если указан
            password_hash = None
            if password:
                if len(password) < 4:
                    return False, "Пароль должен быть не менее 4 символов"
                password_hash = self.auth_manager.hash_password(password)
            
            # Создаем конфигурацию
            config = ServerConfig(
                name=name.strip(),
                ip=ip,
                port=port,
                description=description,
                password_protected=bool(password),
                password_hash=password_hash,
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                config_path="",
                server_path=self._get_server_path(),
                broadcast_port=broadcast_port,
                max_users=max_users,
                auto_start=auto_start,
                is_default=False
            )
            
            # Сохраняем конфигурацию
            if self.save_server_config(config):
                return True, f"Сервер '{name}' успешно создан"
            else:
                return False, "Ошибка сохранения конфигурации"
                
        except Exception as e:
            logger.error(f"Ошибка создания сервера: {e}")
            return False, f"Ошибка создания сервера: {str(e)}"
    
    def _check_port_available(self, ip: str, port: int) -> bool:
        """Проверка доступности порта"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result != 0  # 0 = порт занят
        except:
            return False
    
    def _get_server_path(self) -> str:
        """Получение пути к файлам сервера"""
        # Определяем путь к серверу относительно клиента
        client_dir = Path(__file__).parent
        server_dir = client_dir.parent / "server"
        
        if server_dir.exists():
            return str(server_dir)
        
        # Альтернативные пути
        possible_paths = [
            Path(".") / "server",
            Path("..") / "server",
            Path(__file__).parent.parent.parent / "server"
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        # Если сервер не найден, создаем пустую директорию
        default_path = client_dir.parent / "server"
        default_path.mkdir(exist_ok=True)
        return str(default_path)
    
    def check_server_password(self, server_name: str, password: str) -> bool:
        """
        Проверка пароля сервера.
        
        Args:
            server_name: Имя сервера
            password: Пароль для проверки
            
        Returns:
            True если пароль верный или пароль не требуется
        """
        if server_name not in self.servers:
            logger.warning(f"Сервер не найден: {server_name}")
            return False
        
        config = self.servers[server_name]
        return config.verify_password(password)
    
    def verify_server_credentials(self, server_name: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Проверка учетных данных для запуска сервера.
        
        Args:
            server_name: Имя сервера
            password: Пароль (если требуется)
            
        Returns:
            (успех, сообщение)
        """
        if server_name not in self.servers:
            return False, f"Сервер '{server_name}' не найден"
        
        config = self.servers[server_name]
        
        # Проверка пароля если требуется
        if config.password_protected:
            if not password:
                return False, f"Для сервера '{server_name}' требуется пароль"
            
            if not self.check_server_password(server_name, password):
                return False, "Неверный пароль"
        
        return True, "Учетные данные верны"
    
    def start_server(self, server_name: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Запуск сервера.
        
        Args:
            server_name: Имя сервера
            password: Пароль для запуска (если требуется)
            
        Returns:
            (успех, сообщение)
        """
        try:
            # Проверка существования сервера
            if server_name not in self.servers:
                return False, f"Сервер '{server_name}' не найден"
            
            config = self.servers[server_name]
            
            # Проверка учетных данных
            success, message = self.verify_server_credentials(server_name, password)
            if not success:
                return False, message
            
            # Проверка доступности порта
            if not self._check_port_available(config.ip, config.port):
                return False, f"Порт {config.port} уже используется"
            
            # Проверка существования файлов сервера
            server_path = Path(config.server_path)
            if not server_path.exists():
                return False, f"Файлы сервера не найдены по пути: {config.server_path}"
            
            # Проверка основного файла сервера
            main_py = server_path / "main.py"
            if not main_py.exists():
                # Ищем альтернативные имена
                possible_files = ["main.py", "server.py", "app.py", "start.py"]
                main_file = None
                for filename in possible_files:
                    if (server_path / filename).exists():
                        main_file = server_path / filename
                        break
                
                if not main_file:
                    return False, f"Основной файл сервера не найден в {config.server_path}"
            
            else:
                main_file = main_py
            
            # Формируем команду запуска с передачей пароля если требуется
            python_exec = sys.executable  # Тот же Python что и у клиента
            
            cmd = [
                python_exec,
                str(main_file),
                "--name", f'"{config.name}"',
                "--host", config.ip,
                "--port", str(config.port),
                "--broadcast-port", str(config.broadcast_port),
                "--max-users", str(config.max_users),
                "--description", f'"{config.description}"'
            ]
            
            # Добавляем флаг защиты паролем если требуется
            if config.password_protected:
                cmd.append("--password-protected")
            
            logger.info(f"Запуск сервера: {config.name} на {config.ip}:{config.port}")
            
            # Запускаем сервер в отдельном процессе
            process = subprocess.Popen(
                cmd,
                cwd=str(server_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                shell=True  # Для корректной обработки кавычек в Windows
            )
            
            # Сохраняем процесс
            self.running_servers[server_name] = process
            self.server_processes[server_name] = {
                'process': process,
                'config': config,
                'start_time': time.time(),
                'pid': process.pid
            }
            
            # Запускаем мониторинг вывода
            threading.Thread(
                target=self._monitor_server_output,
                args=(server_name, process),
                daemon=True
            ).start()
            
            # Ждем немного чтобы убедиться что сервер запустился
            time.sleep(3)
            
            # Проверяем что процесс работает
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                error_msg = stderr if stderr else "Сервер завершился при запуске"
                return False, f"Ошибка запуска сервера: {error_msg}"
            
            # Проверяем доступность сервера
            if not self.check_server_connection(server_name):
                return False, "Сервер запущен, но недоступен по сети"
            
            logger.info(f"Сервер '{server_name}' успешно запущен (PID: {process.pid})")
            return True, f"Сервер '{server_name}' запущен на {config.ip}:{config.port}"
            
        except FileNotFoundError as e:
            logger.error(f"Файл не найден при запуске сервера: {e}")
            return False, f"Файл не найден: {e}"
        except Exception as e:
            logger.error(f"Ошибка запуска сервера {server_name}: {e}")
            return False, f"Ошибка запуска: {str(e)}"
    
    def _monitor_server_output(self, server_name: str, process: subprocess.Popen):
        """Мониторинг вывода сервера"""
        try:
            stdout, stderr = process.communicate()
            
            if stdout:
                logger.info(f"[{server_name} stdout]: {stdout}")
            
            if stderr:
                logger.error(f"[{server_name} stderr]: {stderr}")
                
            # Удаляем из списка запущенных после завершения
            if server_name in self.running_servers:
                del self.running_servers[server_name]
            if server_name in self.server_processes:
                del self.server_processes[server_name]
                
            logger.info(f"Сервер '{server_name}' завершил работу")
                
        except Exception as e:
            logger.error(f"Ошибка мониторинга вывода сервера {server_name}: {e}")
    
    def stop_server(self, server_name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Остановка сервера.
        
        Args:
            server_name: Имя сервера
            force: Принудительная остановка
            
        Returns:
            (успех, сообщение)
        """
        if server_name not in self.running_servers:
            return False, f"Сервер '{server_name}' не запущен"
        
        try:
            process = self.running_servers[server_name]
            
            if force:
                process.terminate()
                message = f"Сервер '{server_name}' принудительно остановлен"
            else:
                process.terminate()
                message = f"Сервер '{server_name}' остановлен"
            
            # Ждем завершения
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                message = f"Сервер '{server_name}' принудительно завершен"
            
            # Удаляем из списка запущенных
            del self.running_servers[server_name]
            if server_name in self.server_processes:
                del self.server_processes[server_name]
            
            logger.info(message)
            return True, message
            
        except Exception as e:
            logger.error(f"Ошибка остановки сервера {server_name}: {e}")
            return False, f"Ошибка остановки: {str(e)}"
    
    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """
        Получение статуса сервера.
        
        Args:
            server_name: Имя сервера
            
        Returns:
            Словарь со статусом
        """
        if server_name not in self.servers:
            return {"error": f"Сервер '{server_name}' не найден"}
        
        config = self.servers[server_name]
        is_running = server_name in self.running_servers
        
        status = {
            "name": config.name,
            "ip": config.ip,
            "port": config.port,
            "is_running": is_running,
            "password_protected": config.password_protected,
            "description": config.description,
            "max_users": config.max_users,
            "auto_start": config.auto_start,
            "created_at": config.created_at,
            "config_path": config.config_path
        }
        
        if is_running:
            process_info = self.server_processes.get(server_name, {})
            process = self.running_servers[server_name]
            
            status.update({
                "pid": process.pid,
                "uptime": time.time() - process_info.get('start_time', time.time()),
                "returncode": process.poll()
            })
        
        return status
    
    def delete_server(self, server_name: str, delete_files: bool = False) -> Tuple[bool, str]:
        """
        Удаление сервера.
        
        Args:
            server_name: Имя сервера
            delete_files: Удалять ли файлы конфигурации
            
        Returns:
            (успех, сообщение)
        """
        if server_name not in self.servers:
            return False, f"Сервер '{server_name}' не найден"
        
        try:
            config = self.servers[server_name]
            
            # Останавливаем сервер если запущен
            if server_name in self.running_servers:
                self.stop_server(server_name, force=True)
            
            # Удаляем файл конфигурации
            if delete_files and config.config_path and os.path.exists(config.config_path):
                os.remove(config.config_path)
                logger.info(f"Файл конфигурации удален: {config.config_path}")
            
            # Удаляем из кэша
            del self.servers[server_name]
            
            # Удаляем из процессов если есть
            if server_name in self.server_processes:
                del self.server_processes[server_name]
            
            logger.info(f"Сервер '{server_name}' удален")
            return True, f"Сервер '{server_name}' удален"
            
        except Exception as e:
            logger.error(f"Ошибка удаления сервера {server_name}: {e}")
            return False, f"Ошибка удаления: {str(e)}"
    
    def get_server_list(self) -> List[Dict[str, Any]]:
        """Получение списка всех серверов со статусами"""
        servers = []
        
        for name, config in self.servers.items():
            server_info = self.get_server_status(name)
            servers.append(server_info)
        
        return sorted(servers, key=lambda x: x.get('name', ''))
    
    def update_server_config(
        self,
        server_name: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        Обновление конфигурации сервера.
        
        Args:
            server_name: Имя сервера
            **kwargs: Параметры для обновления
            
        Returns:
            (успех, сообщение)
        """
        if server_name not in self.servers:
            return False, f"Сервер '{server_name}' не найден"
        
        try:
            config = self.servers[server_name]
            
            # Обновляем разрешенные поля
            allowed_fields = ['description', 'max_users', 'auto_start', 'is_default']
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(config, field):
                    setattr(config, field, value)
            
            # Сохраняем обновленную конфигурацию
            if self.save_server_config(config):
                return True, f"Конфигурация сервера '{server_name}' обновлена"
            else:
                return False, "Ошибка сохранения конфигурации"
                
        except Exception as e:
            logger.error(f"Ошибка обновления сервера {server_name}: {e}")
            return False, f"Ошибка обновления: {str(e)}"
    
    def check_server_connection(self, server_name: str, timeout: int = 3) -> bool:
        """
        Проверка подключения к серверу.
        
        Args:
            server_name: Имя сервера
            timeout: Таймаут в секундах
            
        Returns:
            True если сервер доступен
        """
        if server_name not in self.servers:
            return False
        
        config = self.servers[server_name]
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((config.ip, config.port))
            sock.close()
            return result == 0
        except:
            return False
    
    def auto_start_servers(self):
        """Автозапуск серверов с флагом auto_start"""
        logger.info("Проверка серверов для автозапуска...")
        
        for name, config in self.servers.items():
            if config.auto_start and not self.check_server_connection(name):
                logger.info(f"Автозапуск сервера: {name}")
                
                # Для автозапуска не запрашиваем пароль
                # Пользователь должен будет ввести его при подключении
                success, message = self.start_server(name, password=None)
                
                if success:
                    logger.info(f"Сервер {name} автозапущен: {message}")
                else:
                    logger.error(f"Ошибка автозапуска сервера {name}: {message}")
    
    def find_server_by_address(self, ip: str, port: int) -> Optional[str]:
        """
        Поиск сервера по адресу.
        
        Args:
            ip: IP адрес
            port: Порт
            
        Returns:
            Имя сервера или None если не найден
        """
        for name, config in self.servers.items():
            if config.ip == ip and config.port == port:
                return name
        return None
    
    def import_server_from_discovery(self, server_info: ServerInfo, password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Импорт сервера из результатов поиска.
        
        Args:
            server_info: Информация о сервере
            password: Пароль (если требуется)
            
        Returns:
            (успех, сообщение)
        """
        # Проверяем, есть ли уже такой сервер
        existing_name = self.find_server_by_address(server_info.ip, server_info.port)
        if existing_name:
            return True, f"Сервер '{existing_name}' уже существует"
        
        # Создаем новый сервер
        return self.create_server(
            name=server_info.name,
            ip=server_info.ip,
            port=server_info.port,
            description=server_info.description,
            password=password,
            broadcast_port=37020,
            max_users=server_info.max_users,
            auto_start=False
        )
    
    def get_quick_start_server(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Создание быстрого сервера для новичков.
        
        Returns:
            (успех, сообщение, данные сервера)
        """
        try:
            # Получаем локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Ищем свободный порт
            port = 8000
            while port < 8100:
                if self._check_port_available(local_ip, port):
                    break
                port += 1
            
            if port >= 8100:
                return False, "Не удалось найти свободный порт", {}
            
            # Генерируем имя
            import random
            adjectives = ["Быстрый", "Удобный", "Надежный", "Локальный", "Домашний", "Тестовый"]
            nouns = ["Сервер", "Хаб", "Чат", "Мессенджер", "Узел", "Портал"]
            
            name = f"{random.choice(adjectives)} {random.choice(nouns)}"
            
            # Создаем сервер без пароля для простоты
            success, message = self.create_server(
                name=name,
                ip=local_ip,
                port=port,
                description="Автоматически созданный сервер для быстрого старта",
                password=None,
                auto_start=False
            )
            
            if success:
                server_data = {
                    "name": name,
                    "ip": local_ip,
                    "port": port,
                    "description": "Автоматически созданный сервер",
                    "password_protected": False
                }
                return True, message, server_data
            else:
                return False, message, {}
                
        except Exception as e:
            return False, f"Ошибка создания быстрого сервера: {str(e)}", {}


# Глобальный экземпляр для удобного доступа
_server_manager_instance: Optional[ServerManager] = None

def get_server_manager(config_dir: str = None) -> ServerManager:
    """Получение глобального экземпляра ServerManager"""
    global _server_manager_instance
    if _server_manager_instance is None:
        _server_manager_instance = ServerManager(config_dir)
    return _server_manager_instance


# Тестирование модуля
if __name__ == "__main__":
    print("🧪 Тестирование ServerManager...")
    
    # Настройка логгирования для теста
    logging.basicConfig(level=logging.DEBUG)
    
    # Создаем менеджер
    manager = get_server_manager("test_servers")
    
    # Тест создания сервера с паролем
    print("\n1. Тест создания сервера с паролем...")
    success, message = manager.create_server(
        name="Защищенный сервер",
        ip="127.0.0.1",
        port=8888,
        description="Сервер с парольной защитой",
        password="secure123"
    )
    print(f"   Результат: {success} - {message}")
    
    # Тест проверки пароля
    print("\n2. Тест проверки пароля...")
    correct = manager.check_server_password("Защищенный сервер", "secure123")
    print(f"   Правильный пароль: {correct}")
    
    wrong = manager.check_server_password("Защищенный сервер", "wrongpass")
    print(f"   Неправильный пароль: {wrong}")
    
    # Тест получения списка
    print("\n3. Тест получения списка серверов...")
    servers = manager.get_server_list()
    print(f"   Найдено серверов: {len(servers)}")
    for server in servers:
        print(f"   - {server['name']}: {server['ip']}:{server['port']} (пароль: {server['password_protected']})")
    
    # Тест быстрого сервера
    print("\n4. Тест быстрого сервера...")
    success, message, server_data = manager.get_quick_start_server()
    print(f"   Результат: {success} - {message}")
    if success:
        print(f"   Данные сервера: {server_data}")
    
    # Тест удаления сервера
    print("\n5. Тест удаления сервера...")
    success, message = manager.delete_server("Защищенный сервер", delete_files=True)
    print(f"   Результат: {success} - {message}")
    
    # Очистка тестовой директории
    import shutil
    if os.path.exists("test_servers"):
        shutil.rmtree("test_servers")
    
    print("\n✅ Тестирование завершено!")