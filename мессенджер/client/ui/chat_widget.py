from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QLabel, QScrollArea, 
                             QMessageBox, QInputDialog, QFileDialog, QMenu)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QPixmap, QTextImageFormat
import requests
import os
import base64
import tempfile
from datetime import datetime
from models.message import Message
from config import SERVER_URL
from websocket_client import MessengerWebSocket

class ChatWidget(QWidget):
    def __init__(self, auth_token, current_user, contact):
        super().__init__()
        self.auth_token = auth_token
        self.current_user = current_user
        self.contact = contact
        self.messages = []
        self.temp_files = []  # Для хранения временных файлов изображений
        self.init_ui()
        self.load_messages()
        
        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_new_messages)
        self.update_timer.start(5000)  # Check every 5 seconds
        self.websocket = MessengerWebSocket(current_user["id"])
        self.websocket.message_received.connect(self.handle_websocket_message)
        self.websocket.connect()
        
    def handle_websocket_message(self, data):
        """Обработка сообщений от WebSocket"""
        if data.get("type") == "message_deleted":
            message_id = data.get("message_id")
            self._remove_message(message_id)
            
    def _remove_message(self, message_id):
        """Удаление сообщения из интерфейса"""
        # Удаляем из списка сообщений
        self.messages = [msg for msg in self.messages if msg.id != message_id]
        
        # Обновляем отображение
        self.display_messages()
        
    def delete_message(self, message_id):
        """Удаление сообщения с уведомлением через WebSocket"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.delete(f"{SERVER_URL}/messages/{message_id}", headers=headers)
            
            if response.status_code == 200:
                # Локально удаляем сообщение
                self._remove_message(message_id)
                
                # Отправляем уведомление через WebSocket
                notification = {
                    "type": "message_deleted", 
                    "message_id": message_id,
                    "deleted_by": self.current_user["id"]
                }
                self.websocket.send_message(notification)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot delete message: {str(e)}")
            
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Contact info
        contact_layout = QHBoxLayout()
        status_icon = "🟢" if self.contact["is_online"] else "⚫"
        contact_label = QLabel(f"{status_icon} {self.contact['username']}")
        contact_layout.addWidget(contact_label)
        contact_layout.addStretch()
        layout.addLayout(contact_layout)
        
        # Messages area
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        layout.addWidget(self.messages_area)
        
        # Input area
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        self.file_button = QPushButton("📎")
        self.file_button.clicked.connect(self.send_file)
        input_layout.addWidget(self.file_button)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
        self.messages_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.messages_area.customContextMenuRequested.connect(self.show_context_menu)

    def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    file_data = base64.b64encode(f.read()).decode('utf-8')
                
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "content": f"File: {os.path.basename(file_path)}",
                    "receiver_id": self.contact["id"],
                    "message_type": "image",
                    "file_data": file_data
                }
                
                response = requests.post(f"{SERVER_URL}/messages", json=payload, headers=headers)
                
                if response.status_code == 200:
                    message_data = response.json()
                    # Убедимся, что file_data сохраняется в объекте сообщения
                    message_data["file_data"] = file_data  # Сохраняем данные файла
                    message = Message.from_dict(message_data)
                    self.messages.append(message)
                    self.add_message_to_display(message)
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to send file: {str(e)}")
                            
    def show_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Delete Message")
        
        action = menu.exec_(self.messages_area.mapToGlobal(position))
        if action == delete_action:
            self.show_delete_dialog()

    def show_delete_dialog(self):
        message_id, ok = QInputDialog.getInt(self, "Delete Message", "Enter message ID:")
        if ok:
            self.delete_message(message_id)
            
    def load_messages(self):
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{SERVER_URL}/messages?contact_id={self.contact['id']}",
                headers=headers
            )
            
            if response.status_code == 200:
                messages_data = response.json()["messages"]
                self.messages = [Message.from_dict(msg) for msg in messages_data]
                self.display_messages()
            else:
                print("Failed to load messages")
                
        except requests.exceptions.ConnectionError:
            print("Cannot connect to server")
            
    def display_messages(self):
        self.messages_area.clear()
        for message in sorted(self.messages, key=lambda x: x.timestamp):
            self.add_message_to_display(message)
            
    def add_message_to_display(self, message: Message):
        cursor = self.messages_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Определяем отправителя и стили
        is_outgoing = message.is_outgoing(self.current_user["id"])
        sender_name = "Вы" if is_outgoing else self.contact["username"]
        alignment = Qt.AlignRight if is_outgoing else Qt.AlignLeft
        bg_color = "#e3f2fd" if is_outgoing else "#f5f5f5"
        text_color = "#1976d2" if is_outgoing else "#333333"
        
        # Для изображений создаем временный файл и отображаем картинку
        if message.message_type == "image" and hasattr(message, 'file_data') and message.file_data:
            try:
                # Декодируем base64 и создаем временный файл
                image_data = base64.b64decode(message.file_data)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_file.write(image_data)
                temp_file.close()
                self.temp_files.append(temp_file.name)  # Сохраняем для очистки
                
                # Добавляем заголовок с именем отправителя и временем
                header_html = f"""
                <div class="message-header" style="text-align: {alignment}; margin-bottom: 5px;">
                    <span style="font-size: 12px; color: {text_color}; font-weight: bold;">
                        {sender_name} • {message.get_formatted_time()}
                    </span>
                </div>
                """
                self.messages_area.append(header_html)
                
                # Добавляем изображение в текст
                image_format = QTextImageFormat()
                image_format.setName(temp_file.name)
                image_format.setWidth(200)  # Ограничиваем ширину
                cursor.insertImage(image_format)
                
                # Добавляем ID сообщения под изображением
                footer_html = f"""
                <div class="message-footer" style="text-align: {alignment}; margin-top: 5px;">
                    <span style="font-size: 10px; color: #999;">
                        ID: {message.id}
                    </span>
                </div>
                <div style="clear: both; margin-bottom: 15px;"></div>
                """
                self.messages_area.append(footer_html)
                
            except Exception as e:
                print(f"Error displaying image: {e}")
                # Fallback to text representation
                self.add_text_message(message, sender_name, alignment, bg_color, text_color)
        else:
            # Обычное текстовое сообщение
            self.add_text_message(message, sender_name, alignment, bg_color, text_color)
        
        self.messages_area.ensureCursorVisible()

    def add_text_message(self, message: Message, sender_name: str, alignment: str, bg_color: str, text_color: str):
        """Добавление текстового сообщения с полной информацией"""
        html = f"""
        <div class="message" data-message-id="{message.id}" style="margin: 5px; padding: 10px; background-color: {bg_color}; 
                    border-radius: 10px; text-align: {alignment}; float: {alignment}; 
                    clear: both; max-width: 70%;">
            <div style="font-size: 12px; color: {text_color}; font-weight: bold; margin-bottom: 5px;">
                {sender_name} • {message.get_formatted_time()}
            </div>
            <div style="margin-top: 5px; color: #333;">
                {message.content}
            </div>
            <div style="font-size: 10px; color: #999; margin-top: 5px;">
                ID: {message.id}
            </div>
        </div>
        <div style="clear: both; margin-bottom: 15px;"></div>
        """
        self.messages_area.append(html)
        
    def send_message(self):
        message_text = self.message_input.text().strip()
        if not message_text:
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "content": message_text,
                "receiver_id": self.contact["id"],
                "message_type": "text"
            }
            
            print(f"🔧 Debug - Sending message to: {SERVER_URL}/messages")
            print(f"🔧 Debug - Headers: {headers}")
            print(f"🔧 Debug - Payload: {payload}")
            print(f"🔧 Debug - Contact ID: {self.contact['id']}")
            
            response = requests.post(
                f"{SERVER_URL}/messages",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            print(f"🔧 Debug - Response Status: {response.status_code}")
            print(f"🔧 Debug - Response Text: {response.text}")
            
            if response.status_code == 200:
                self.message_input.clear()
                message_data = response.json()
                message = Message.from_dict(message_data)
                self.messages.append(message)
                self.add_message_to_display(message)
                print("✅ Message sent successfully!")
            else:
                print(f"❌ Failed to send message. Status: {response.status_code}")
                print(f"❌ Response: {response.text}")
                
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                    QMessageBox.warning(self, "Error", f"Failed to send message: {error_detail}")
                except:
                    QMessageBox.warning(self, "Error", f"Failed to send message. Status: {response.status_code}")
                    
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Error", "Cannot connect to server")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")
            print(f"❌ Unexpected error: {e}")
            
    def check_new_messages(self):
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{SERVER_URL}/messages/unread",
                headers=headers
            )
            
            if response.status_code == 200:
                unread_messages = response.json()["messages"]
                for msg_data in unread_messages:
                    message = Message.from_dict(msg_data)
                    if message.sender_id == self.contact["id"]:
                        self.messages.append(message)
                        self.add_message_to_display(message)
                        # Mark as read
                        requests.put(
                            f"{SERVER_URL}/messages/{message.id}/read",
                            headers=headers
                        )
                        
        except requests.exceptions.ConnectionError:
            pass
            
    def update_contact_status(self):
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{SERVER_URL}/users/{self.contact['id']}", headers=headers)
            if response.status_code == 200:
                self.contact = response.json()
        except:
            pass
            
    def closeEvent(self, event):
        # Очищаем временные файлы при закрытии
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        event.accept()