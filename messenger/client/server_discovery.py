"""
Модуль для обнаружения доступных серверов в локальной сети через UDP broadcast.
Интегрирован с BroadcastClient.
"""

import threading
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from models.server_info import ServerInfo

# Импортируем BroadcastClient
try:
    from network.broadcast_client import BroadcastClient, get_broadcast_client
except ImportError:
    # Fallback для прямой структуры
    from broadcast_client import BroadcastClient, get_broadcast_client

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DiscoveryConfig:
    """Конфигурация для обнаружения серверов"""
    timeout: float = 3.0  # секунды
    discovery_interval: int = 30  # секунды между автоматическими поисками
    max_cache_age: int = 300  # секунд жизни кэша серверов


class ServerDiscovery:
    """
    Класс для обнаружения серверов мессенджера в локальной сети.
    Использует BroadcastClient для поиска серверов.
    """
    
    def __init__(self, config: Optional[DiscoveryConfig] = None):
        """
        Инициализация модуля обнаружения серверов.
        
        Args:
            config: Конфигурация обнаружения (используется дефолтная если None)
        """
        self.config = config or DiscoveryConfig()
        self.broadcast_client = get_broadcast_client()
        
        self.found_servers: Dict[str, ServerInfo] = {}  # ip:port -> ServerInfo
        self.discovery_thread: Optional[threading.Thread] = None
        self.is_discovering = False
        self.last_discovery_time = 0
        self.callbacks = []
        
        logger.info("ServerDiscovery инициализирован с интеграцией BroadcastClient")
    
    def discover(self) -> List[ServerInfo]:
        """
        Активный поиск серверов в сети.
        
        Returns:
            Список обнаруженных серверов
        """
        logger.info("Начинаю поиск серверов в сети...")
        servers = []
        
        try:
            # Используем BroadcastClient для поиска
            found_servers = self.broadcast_client.discover_servers()
            
            # Обновляем кэш найденных серверов
            for server in found_servers:
                server_key = f"{server.ip}:{server.port}"
                
                # Обновляем или добавляем сервер
                if server_key in self.found_servers:
                    self.found_servers[server_key].last_seen = time.time()
                    self.found_servers[server_key].is_online = True
                else:
                    server.last_seen = time.time()
                    self.found_servers[server_key] = server
                
                servers.append(server)
                logger.info(f"Найден сервер: {server.name} ({server.ip}:{server.port})")
            
            # Помечаем старые серверы как оффлайн
            self._mark_offline_servers()
            
            logger.info(f"Поиск завершен. Найдено серверов: {len(servers)}")
            
        except Exception as e:
            logger.error(f"Ошибка при поиске серверов: {e}")
        
        self.last_discovery_time = time.time()
        return list(self.found_servers.values())
    
    def quick_discover(self) -> List[ServerInfo]:
        """
        Быстрый поиск серверов с меньшим таймаутом.
        
        Returns:
            Список найденных серверов
        """
        logger.info("Быстрый поиск серверов...")
        
        try:
            # Используем быстрый поиск BroadcastClient
            original_timeout = self.broadcast_client.timeout
            self.broadcast_client.timeout = 1.5
            
            servers = self.discover()
            
            # Восстанавливаем таймаут
            self.broadcast_client.timeout = original_timeout
            
            return servers
            
        except Exception as e:
            logger.error(f"Ошибка быстрого поиска серверов: {e}")
            return []
    
    def _mark_offline_servers(self):
        """Помечает серверы как оффлайн если они не отвечали долгое время"""
        current_time = time.time()
        offline_timeout = self.config.max_cache_age
        
        for server_key, server in list(self.found_servers.items()):
            if server.last_seen and (current_time - server.last_seen) > offline_timeout:
                server.is_online = False
                logger.debug(f"Сервер {server.name} помечен как оффлайн")
    
    def start_continuous_discovery(self):
        """
        Запуск непрерывного фонового поиска серверов.
        """
        if self.is_discovering:
            logger.warning("Поиск уже запущен")
            return
        
        self.is_discovering = True
        self.discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True,
            name="ServerDiscoveryThread"
        )
        self.discovery_thread.start()
        logger.info("Запущен фоновый поиск серверов")
    
    def _discovery_loop(self):
        """Фоновый цикл поиска серверов"""
        while self.is_discovering:
            try:
                servers = self.discover()
                
                # Вызываем колбэки если есть новые серверы
                if servers and self.callbacks:
                    for callback in self.callbacks:
                        try:
                            callback(servers)
                        except Exception as e:
                            logger.error(f"Ошибка в колбэке: {e}")
                
                # Ждем перед следующим поиском
                time.sleep(self.config.discovery_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле поиска: {e}")
                time.sleep(5)  # Краткая пауза при ошибке
    
    def stop_continuous_discovery(self):
        """Остановка фонового поиска"""
        self.is_discovering = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=2)
        logger.info("Фоновый поиск серверов остановлен")
    
    def add_callback(self, callback):
        """
        Добавление callback функции, которая вызывается при обнаружении новых серверов.
        
        Args:
            callback: Функция, принимающая список ServerInfo
        """
        if callable(callback):
            self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        """Удаление callback функции"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_online_servers(self) -> List[ServerInfo]:
        """
        Получение списка только онлайн серверов.
        
        Returns:
            Список онлайн серверов
        """
        return [server for server in self.found_servers.values() if server.is_online]
    
    def get_server_by_address(self, ip: str, port: int) -> Optional[ServerInfo]:
        """
        Поиск сервера по адресу.
        
        Args:
            ip: IP адрес сервера
            port: Порт сервера
            
        Returns:
            ServerInfo или None если не найден
        """
        server_key = f"{ip}:{port}"
        return self.found_servers.get(server_key)
    
    def clear_cache(self):
        """Очистка кэша найденных серверов"""
        self.found_servers.clear()
        logger.info("Кэш серверов очищен")
    
    def check_server_availability(self, ip: str, port: int, timeout: float = 2.0) -> bool:
        """
        Проверка доступности конкретного сервера.
        
        Args:
            ip: IP адрес сервера
            port: Порт сервера
            timeout: Таймаут проверки
            
        Returns:
            True если сервер доступен
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False


# Синглтон для глобального доступа
_discovery_instance: Optional[ServerDiscovery] = None

def get_discovery_instance() -> ServerDiscovery:
    """Получение глобального экземпляра ServerDiscovery"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = ServerDiscovery()
    return _discovery_instance


def discover_servers_once() -> List[ServerInfo]:
    """
    Упрощенная функция для одноразового поиска серверов.
    
    Returns:
        Список найденных серверов
    """
    return get_discovery_instance().discover()


def quick_discover_servers() -> List[ServerInfo]:
    """
    Быстрый одноразовый поиск серверов.
    
    Returns:
        Список найденных серверов
    """
    return get_discovery_instance().quick_discover()


# Тестирование модуля
if __name__ == "__main__":
    print("Тестирование модуля обнаружения серверов...")
    
    # Создаем конфигурацию с быстрым таймаутом для теста
    test_config = DiscoveryConfig(timeout=1.0)
    discovery = ServerDiscovery(test_config)
    
    print("Быстрый поиск серверов...")
    
    servers = discovery.quick_discover()
    
    if servers:
        print(f"\nНайдено серверов: {len(servers)}")
        for i, server in enumerate(servers, 1):
            print(f"\n{i}. {server.name}")
            print(f"   Адрес: {server.ip}:{server.port}")
            print(f"   Пользователей: {server.users_count}")
            print(f"   Требуется пароль: {'Да' if server.is_password_protected else 'Нет'}")
            print(f"   Описание: {server.description}")
            print(f"   Статус: {'🟢 Онлайн' if server.is_online else '⚫ Оффлайн'}")
    else:
        print("Серверы не найдены.")
    
    print("\nТест завершен.")