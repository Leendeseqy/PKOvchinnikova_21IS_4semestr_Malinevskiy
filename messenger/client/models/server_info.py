"""
Модель данных для информации о сервере.
"""

from dataclasses import dataclass
from typing import Optional
import json


@dataclass
class ServerInfo:
    """Информация о сервере мессенджера"""
    
    name: str                    # Имя сервера
    ip: str                      # IP адрес
    port: int                    # Порт
    users_count: int = 0         # Количество пользователей онлайн
    is_password_protected: bool = False  # Требуется пароль для запуска
    description: str = ""        # Описание сервера
    version: str = "1.0"         # Версия сервера
    max_users: int = 50          # Максимальное количество пользователей
    is_online: bool = True       # Онлайн статус
    last_seen: Optional[float] = None  # Время последнего ответа (timestamp)
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "users_count": self.users_count,
            "is_password_protected": self.is_password_protected,
            "description": self.description,
            "version": self.version,
            "max_users": self.max_users,
            "is_online": self.is_online,
            "last_seen": self.last_seen
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ServerInfo':
        """Создание из словаря"""
        return cls(
            name=data["name"],
            ip=data["ip"],
            port=data["port"],
            users_count=data.get("users_count", 0),
            is_password_protected=data.get("is_password_protected", False),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            max_users=data.get("max_users", 50),
            is_online=data.get("is_online", True),
            last_seen=data.get("last_seen")
        )
    
    def to_json(self) -> str:
        """Сериализация в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ServerInfo':
        """Десериализация из JSON"""
        return cls.from_dict(json.loads(json_str))
    
    @property
    def address(self) -> str:
        """Полный адрес сервера (ip:port)"""
        return f"{self.ip}:{self.port}"
    
    @property
    def url(self) -> str:
        """URL сервера для HTTP подключения"""
        return f"http://{self.ip}:{self.port}"
    
    @property
    def ws_url(self) -> str:
        """URL для WebSocket подключения"""
        return f"ws://{self.ip}:{self.port}/ws"
    
    def __str__(self) -> str:
        """Строковое представление"""
        status = "🟢" if self.is_online else "⚫"
        password = " 🔒" if self.is_password_protected else ""
        users = f" 👥{self.users_count}" if self.users_count > 0 else ""
        return f"{status} {self.name} - {self.address}{users}{password}"
    
    def __eq__(self, other: object) -> bool:
        """Сравнение серверов по адресу"""
        if not isinstance(other, ServerInfo):
            return False
        return self.ip == other.ip and self.port == other.port
    
    def __hash__(self) -> int:
        """Хэш для использования в словарях"""
        return hash((self.ip, self.port))