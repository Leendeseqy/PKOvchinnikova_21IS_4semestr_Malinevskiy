"""
Основные модели данных для базы данных сервера.
Включает MessageModel с поддержкой временных зон.
"""

from database.db import get_db_connection
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3
from typing import List, Optional
from enum import Enum
import os

class MessageModel:
    """Модель для работы с сообщениями в базе данных"""
    
    @staticmethod
    def create_message(sender_id: int, receiver_id: int, content: str, 
                     message_type: str = "text", file_data: Optional[str] = None) -> int:
        """
        Создание нового сообщения
        
        Args:
            sender_id: ID отправителя
            receiver_id: ID получателя
            content: Текст сообщения или описание файла
            message_type: Тип сообщения ('text', 'image', 'file')
            file_data: Данные файла в base64 (для изображений)
            
        Returns:
            ID созданного сообщения
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Используем московское время
        now = datetime.now(tz=ZoneInfo("Europe/Moscow"))

        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, content, message_type, file_data, timestamp, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sender_id, receiver_id, content, message_type, file_data, now, False))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return message_id

    @staticmethod
    def get_messages_between_users(user1_id: int, user2_id: int, limit: int = 100) -> List[dict]:
        """
        Получение истории переписки между двумя пользователями
        
        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            Список сообщений с информацией об отправителе и получателе
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.*, u1.username as sender_username, u2.username as receiver_username
            FROM messages m
            JOIN users u1 ON m.sender_id = u1.id
            JOIN users u2 ON m.receiver_id = u2.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?)
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.timestamp DESC
            LIMIT ?
        """, (user1_id, user2_id, user2_id, user1_id, limit))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages

    @staticmethod
    def get_unread_messages(user_id: int) -> List[dict]:
        """
        Получение непрочитанных сообщений пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список непрочитанных сообщений
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.*, u.username as sender_username
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.receiver_id = ? AND m.is_read = FALSE
            ORDER BY m.timestamp
        """, (user_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages

    @staticmethod
    def mark_as_read(message_id: int):
        """
        Отметка сообщения как прочитанного
        
        Args:
            message_id: ID сообщения
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE messages SET is_read = TRUE WHERE id = ?
        """, (message_id,))
        
        conn.commit()
        conn.close()

    @staticmethod
    def delete_message(message_id: int):
        """
        Удаление сообщения из базы данных
        
        Args:
            message_id: ID сообщения
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
        conn.close()
        
    @staticmethod
    def get_message_by_id(message_id: int) -> Optional[dict]:
        """
        Получение сообщения по ID
        
        Args:
            message_id: ID сообщения
            
        Returns:
            Сообщение или None если не найдено
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.*, u1.username as sender_username, u2.username as receiver_username
            FROM messages m
            JOIN users u1 ON m.sender_id = u1.id
            JOIN users u2 ON m.receiver_id = u2.id
            WHERE m.id = ?
        """, (message_id,))
        
        message = cursor.fetchone()
        conn.close()
        
        return dict(message) if message else None


class MessageType(str, Enum):
    """Типы сообщений"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


class UserStatus(str, Enum):
    """Статусы пользователей"""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


class ServerStatus(str, Enum):
    """Статусы серверов"""
    RUNNING = "running"
    STOPPED = "stopped"
    MAINTENANCE = "maintenance"