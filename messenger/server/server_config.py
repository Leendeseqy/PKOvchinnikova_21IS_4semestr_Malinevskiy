"""
Конфигурация сервера Local Messenger.
Включает настройки парольной защиты и автозапуска.
"""

import json
import os
import hashlib
import socket
from pathlib import Path
from typing import Optional, Dict, Any


class ServerConfig:
    """Класс для управления конфигурацией сервера"""
    
    def __init__(self, config_path: str = "server_config.json"):
        """
        Инициализация конфигурации сервера.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.default_config = {
            "server_name": "Local Messenger Server",
            "description": "Сервер локального мессенджера",
            "host": "0.0.0.0",
            "port": 8000,
            "broadcast_port": 37020,
            "max_users": 50,
            "password_protected": False,
            "password_hash": None,
            "salt": None,
            "version": "1.0",
            "auto_start": False,
            "created_at": "",
            "is_default": True
        }
        
        self.config = self.default_config.copy()
        self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # Обновляем только существующие ключи
                for key in self.config:
                    if key in loaded_config:
                        self.config[key] = loaded_config[key]
                
                print(f"✅ Конфигурация загружена из {self.config_path}")
            else:
                self.save_config()  # Создаем файл с настройками по умолчанию
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации: {e}")
            self.config = self.default_config.copy()
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            # Создаем директорию если не существует
            self.config_path.parent.mkdir(exist_ok=True, parents=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Конфигурация сохранена в {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения конфигурации: {e}")
            return False
    
    def set_password(self, password: str):
        """
        Установка пароля для сервера.
        
        Args:
            password: Пароль для защиты сервера
        """
        if not password:
            self.config["password_protected"] = False
            self.config["password_hash"] = None
            self.config["salt"] = None
            return True
        
        try:
            # Генерируем соль
            import secrets
            salt = secrets.token_hex(16)
            
            # Хэшируем пароль с солью
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            self.config["password_protected"] = True
            self.config["password_hash"] = password_hash
            self.config["salt"] = salt
            
            print("✅ Пароль установлен")
            return True
        except Exception as e:
            print(f"❌ Ошибка установки пароля: {e}")
            return False
    
    def verify_password(self, password: str) -> bool:
        """
        Проверка пароля.
        
        Args:
            password: Пароль для проверки
            
        Returns:
            True если пароль верный или пароль не требуется
        """
        if not self.config["password_protected"]:
            return True
        
        if not self.config["password_hash"] or not self.config["salt"]:
            return False
        
        try:
            # Проверяем пароль
            password_hash = hashlib.sha256(
                (password + self.config["salt"]).encode()
            ).hexdigest()
            
            return password_hash == self.config["password_hash"]
        except:
            return False
    
    def update_config(self, **kwargs):
        """
        Обновление конфигурации.
        
        Args:
            **kwargs: Параметры для обновления
        """
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
        
        self.save_config()
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Получение информации о сервере для broadcast.
        
        Returns:
            Словарь с информацией о сервере
        """
        return {
            "name": self.config["server_name"],
            "port": self.config["port"],
            "description": self.config["description"],
            "version": self.config["version"],
            "max_users": self.config["max_users"],
            "password_required": self.config["password_protected"],
            "users_count": self.get_online_users_count(),
            "host": self.get_server_host()
        }
    
    def get_online_users_count(self) -> int:
        """Получение количества онлайн пользователей"""
        # Эта функция будет интегрирована с UserModel
        try:
            from database.user_model import UserModel
            users = UserModel.get_all_users()
            return len([u for u in users if u.get("is_online", False)])
        except:
            return 0
    
    def get_server_host(self) -> str:
        """Получение IP адреса сервера"""
        try:
            if self.config["host"] in ["0.0.0.0", ""]:
                # Получаем локальный IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                return local_ip
            return self.config["host"]
        except:
            return "127.0.0.1"
    
    def get_broadcast_info(self) -> Dict[str, Any]:
        """Получение информации для broadcast"""
        info = self.get_server_info()
        info.update({
            "type": "server_response",
            "timestamp": "",  # Заполняется при отправке
            "broadcast_port": self.config["broadcast_port"]
        })
        return info
    
    def is_protected(self) -> bool:
        """Проверка защиты паролем"""
        return self.config["password_protected"]
    
    def require_password(self) -> bool:
        """Требуется ли пароль для запуска"""
        return self.config["password_protected"]
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Получение сводки конфигурации"""
        return {
            "basic": {
                "name": self.config["server_name"],
                "description": self.config["description"],
                "version": self.config["version"]
            },
            "network": {
                "host": self.config["host"],
                "port": self.config["port"],
                "broadcast_port": self.config["broadcast_port"],
                "actual_ip": self.get_server_host()
            },
            "security": {
                "password_protected": self.config["password_protected"],
                "auto_start": self.config["auto_start"]
            },
            "limits": {
                "max_users": self.config["max_users"]
            }
        }


# Глобальный экземпляр конфигурации
_server_config_instance: Optional[ServerConfig] = None

def get_server_config(config_path: str = "server_config.json") -> ServerConfig:
    """Получение глобального экземпляра конфигурации сервера"""
    global _server_config_instance
    if _server_config_instance is None:
        _server_config_instance = ServerConfig(config_path)
    return _server_config_instance


def init_server_config_from_args(args) -> ServerConfig:
    """
    Инициализация конфигурации из аргументов командной строки.
    
    Args:
        args: Аргументы командной строки
        
    Returns:
        Экземпляр ServerConfig
    """
    config = get_server_config()
    
    # Обновляем конфигурацию из аргументов
    updates = {}
    
    if hasattr(args, 'name') and args.name:
        updates["server_name"] = args.name
    
    if hasattr(args, 'host') and args.host:
        updates["host"] = args.host
    
    if hasattr(args, 'port') and args.port:
        updates["port"] = args.port
    
    if hasattr(args, 'broadcast_port') and args.broadcast_port:
        updates["broadcast_port"] = args.broadcast_port
    
    if hasattr(args, 'max_users') and args.max_users:
        updates["max_users"] = args.max_users
    
    if hasattr(args, 'description') and args.description:
        updates["description"] = args.description
    
    if hasattr(args, 'password_protected') and args.password_protected:
        updates["password_protected"] = True
    
    if hasattr(args, 'auto_start') and args.auto_start is not None:
        updates["auto_start"] = args.auto_start
    
    if updates:
        config.update_config(**updates)
    
    # Устанавливаем время создания если его нет
    if not config.config.get("created_at"):
        from datetime import datetime
        config.update_config(created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return config


if __name__ == "__main__":
    print("🧪 Тестирование конфигурации сервера...")
    
    # Создаем конфигурацию
    config = ServerConfig("test_config.json")
    
    print("\n📋 Текущая конфигурация:")
    summary = config.get_config_summary()
    
    for section, values in summary.items():
        print(f"\n{section.upper()}:")
        for key, value in values.items():
            print(f"  {key}: {value}")
    
    # Тест пароля
    print("\n🔐 Тест пароля:")
    
    config.set_password("mypassword123")
    print(f"Пароль установлен: {config.is_protected()}")
    
    print(f"Проверка правильного пароля: {config.verify_password('mypassword123')}")
    print(f"Проверка неправильного пароля: {config.verify_password('wrongpassword')}")
    
    # Тест информации о сервере
    print("\n🌐 Информация для broadcast:")
    server_info = config.get_server_info()
    for key, value in server_info.items():
        print(f"  {key}: {value}")
    
    # Удаляем тестовый файл
    import os
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    print("\n✅ Тест завершен!")