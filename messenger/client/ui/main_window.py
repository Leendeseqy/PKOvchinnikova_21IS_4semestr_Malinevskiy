"""
Главное окно клиента Local Messenger.
"""

from PyQt5.QtWidgets import (QMainWindow, QSplitter, QTabWidget, QListWidget,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                             QStatusBar, QMenuBar, QAction, QMessageBox,
                             QSystemTrayIcon, QMenu, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QIcon, QCursor
import requests
import sys

# Импорт модулей из новой структуры
try:
    from config import SERVER_URL, APP_NAME, APP_VERSION, update_server_config
    from ui.chat_widget import ChatWidget
    from utils.auth_manager import get_auth_manager
    from models.user import User
except ImportError as e:
    print(f"Ошибка импорта в main_window.py: {e}")


class MainWindow(QMainWindow):
    connection_status_changed = pyqtSignal(bool)
    
    def __init__(self, auth_token, current_user, server_url=None):
        super().__init__()
        self.auth_token = auth_token
        self.current_user = current_user
        self.server_url = server_url or SERVER_URL
        
        # Инициализация менеджеров
        self.auth_manager = get_auth_manager()
        
        self.contacts = []
        self.unread_messages = {}
        self.system_tray = None
        
        self.init_ui()
        self.init_tray()
        self.load_contacts()
        
        # Таймер для автообновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_contacts)
        self.update_timer.start(10000)  # Обновлять каждые 10 секунд
        
        # Таймер для проверки соединения
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(5000)  # Проверять каждые 5 секунд

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} - {self.current_user.get('username', 'Пользователь')}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Устанавливаем иконку
        try:
            self.setWindowIcon(QIcon("icon.ico"))
        except:
            pass
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Панель пользователя
        user_panel = self.create_user_panel()
        splitter.addWidget(user_panel)
        
        # Contacts list
        contacts_panel = QWidget()
        contacts_layout = QVBoxLayout()
        
        contacts_label = QLabel("Контакты")
        contacts_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        contacts_layout.addWidget(contacts_label)
        
        self.contacts_list = QListWidget()
        self.contacts_list.currentRowChanged.connect(self.on_contact_selected)
        self.contacts_list.setStyleSheet("""
            QListWidget {
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        contacts_layout.addWidget(self.contacts_list)
        
        contacts_panel.setLayout(contacts_layout)
        splitter.addWidget(contacts_panel)
        
        # Chat area
        self.chat_tabs = QTabWidget()
        self.chat_tabs.setTabsClosable(True)
        self.chat_tabs.tabCloseRequested.connect(self.close_chat_tab)
        self.chat_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #1976d2;
            }
            QTabBar::tab:hover {
                background-color: #e8e8e8;
            }
        """)
        splitter.addWidget(self.chat_tabs)
        
        splitter.setSizes([200, 300, 700])
        layout.addWidget(splitter)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Status bar
        self.statusBar().showMessage("✅ Подключено")
        self.statusBar().setStyleSheet("color: #4CAF50;")
        
    def create_user_panel(self):
        """Создание панели пользователя"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #1976d2;
                color: white;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)
        
        # Аватар (заглушка)
        avatar_label = QLabel("👤")
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                padding: 10px;
            }
        """)
        layout.addWidget(avatar_label)
        
        # Имя пользователя
        username_label = QLabel(self.current_user.get('username', 'Пользователь'))
        username_label.setAlignment(Qt.AlignCenter)
        username_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 16px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(username_label)
        
        # Статус
        status = "🟢 В сети" if self.current_user.get('is_online', False) else "⚫ Не в сети"
        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                margin-bottom: 15px;
            }
        """)
        layout.addWidget(status_label)
        
        # Разделитель
        separator = QLabel()
        separator.setStyleSheet("""
            QLabel {
                border-top: 1px solid rgba(255, 255, 255, 0.3);
                margin: 10px 0;
            }
        """)
        layout.addWidget(separator)
        
        # Кнопки действий
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(5)
        
        # Кнопка настроек
        settings_btn = QLabel("⚙️ Настройки")
        settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        settings_btn.mousePressEvent = lambda e: self.show_settings()
        settings_btn.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                font-size: 13px;
            }
            QLabel:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        actions_layout.addWidget(settings_btn)
        
        # Кнопка смены сервера
        change_server_btn = QLabel("🔄 Сменить сервер")
        change_server_btn.setCursor(QCursor(Qt.PointingHandCursor))
        change_server_btn.mousePressEvent = lambda e: self.change_server()
        change_server_btn.setStyleSheet("""
            QLabel {
                padding: 8px;
                border-radius: 4px;
                font-size: 13px;
            }
            QLabel:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        actions_layout.addWidget(change_server_btn)
        
        layout.addLayout(actions_layout)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        # Информация о сервере
        server_info = QLabel(f"Сервер: {self.server_url}")
        server_info.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: rgba(255, 255, 255, 0.7);
                margin-top: 10px;
            }
        """)
        layout.addWidget(server_info)
        
        panel.setLayout(layout)
        return panel
        
    def create_menu_bar(self):
        """Создание меню"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("Файл")
        
        # Настройки
        settings_action = QAction("⚙️ Настройки", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        # Сменить сервер
        change_server_action = QAction("🔄 Сменить сервер", self)
        change_server_action.triggered.connect(self.change_server)
        file_menu.addAction(change_server_action)
        
        file_menu.addSeparator()
        
        # Выход
        logout_action = QAction("🚪 Выйти", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("Вид")
        
        refresh_action = QAction("🔄 Обновить", self)
        refresh_action.triggered.connect(self.load_contacts)
        view_menu.addAction(refresh_action)
        
        toggle_tray_action = QAction("📌 Показать/скрыть в трее", self)
        toggle_tray_action.triggered.connect(self.toggle_tray)
        view_menu.addAction(toggle_tray_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Помощь")
        
        about_action = QAction("ℹ️ О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("❓ Справка", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
    def init_tray(self):
        """Инициализация системного трея"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.system_tray = QSystemTrayIcon(self)
        
        try:
            self.system_tray.setIcon(QIcon("icon.ico"))
        except:
            pass
        
        # Меню трея
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Показать")
        show_action.triggered.connect(self.show_window)
        
        hide_action = tray_menu.addAction("Скрыть")
        hide_action.triggered.connect(self.hide_window)
        
        tray_menu.addSeparator()
        
        logout_action = tray_menu.addAction("Выйти")
        logout_action.triggered.connect(self.logout)
        
        exit_action = tray_menu.addAction("Выход")
        exit_action.triggered.connect(self.close)
        
        self.system_tray.setContextMenu(tray_menu)
        self.system_tray.activated.connect(self.tray_activated)
        self.system_tray.show()
        
    def tray_activated(self, reason):
        """Обработка клика по иконке в трее"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide_window()
            else:
                self.show_window()
                
    def show_window(self):
        """Показать окно"""
        self.show()
        self.activateWindow()
        self.raise_()
        
    def hide_window(self):
        """Скрыть окно в трей"""
        self.hide()
        if self.system_tray:
            self.system_tray.showMessage(
                APP_NAME,
                "Приложение свернуто в системный трей",
                QSystemTrayIcon.Information,
                2000
            )
            
    def toggle_tray(self):
        """Переключить отображение в трее"""
        if self.system_tray:
            if self.system_tray.isVisible():
                self.system_tray.hide()
            else:
                self.system_tray.show()
                
    def load_contacts(self):
        """Загрузка списка контактов"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{self.server_url}/users",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.contacts = response.json()
                self.update_contacts_list()
                self.statusBar().showMessage("✅ Контакты загружены")
            else:
                self.statusBar().showMessage("⚠️ Ошибка загрузки контактов")
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить контакты")
                
        except requests.exceptions.ConnectionError:
            self.statusBar().showMessage("❌ Нет подключения")
            self.connection_status_changed.emit(False)
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к серверу")
        except Exception as e:
            self.statusBar().showMessage(f"⚠️ Ошибка: {str(e)}")
            
    def update_contacts_list(self):
        """Обновление списка контактов"""
        self.contacts_list.clear()
        
        # Фильтруем текущего пользователя
        filtered_contacts = [
            user for user in self.contacts 
            if user["id"] != self.current_user["id"]
        ]
        
        # Сортируем: сначала онлайн, потом по имени
        sorted_contacts = sorted(
            filtered_contacts,
            key=lambda x: (not x["is_online"], x["username"].lower())
        )
        
        for user in sorted_contacts:
            status_icon = "🟢" if user["is_online"] else "⚫"
            
            # Добавляем счетчик непрочитанных сообщений
            unread_count = self.unread_messages.get(user["id"], 0)
            unread_text = f" ({unread_count})" if unread_count > 0 else ""
            
            item_text = f"{status_icon} {user['username']}{unread_text}"
            self.contacts_list.addItem(item_text)
            
    def update_contacts(self):
        """Обновление списка контактов"""
        self.load_contacts()
        
    def check_connection(self):
        """Проверка соединения с сервером"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{self.server_url}/users/me",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.statusBar().showMessage("✅ Подключено")
                self.statusBar().setStyleSheet("color: #4CAF50;")
                self.connection_status_changed.emit(True)
            else:
                self.statusBar().showMessage("⚠️ Проблемы с подключением")
                self.statusBar().setStyleSheet("color: #FF9800;")
                self.connection_status_changed.emit(False)
                
        except:
            self.statusBar().showMessage("❌ Нет подключения")
            self.statusBar().setStyleSheet("color: #F44336;")
            self.connection_status_changed.emit(False)
            
    def on_contact_selected(self, row):
        """Обработка выбора контакта"""
        if row >= 0:
            # Фильтруем текущего пользователя
            filtered_contacts = [
                user for user in self.contacts 
                if user["id"] != self.current_user["id"]
            ]
            
            if row < len(filtered_contacts):
                contact = filtered_contacts[row]
                self.open_chat(contact)
                
    def open_chat(self, contact):
        """Открытие чата с контактом"""
        print(f"🔧 Opening chat with: {contact['username']} (ID: {contact['id']})")
        
        # Check if chat already open
        for i in range(self.chat_tabs.count()):
            chat_widget = self.chat_tabs.widget(i)
            if hasattr(chat_widget, 'contact') and chat_widget.contact["id"] == contact["id"]:
                self.chat_tabs.setCurrentIndex(i)
                # Очищаем счетчик непрочитанных
                if contact["id"] in self.unread_messages:
                    del self.unread_messages[contact["id"]]
                    self.update_contacts_list()
                return
        
        # Create new chat tab
        try:
            chat_widget = ChatWidget(self.auth_token, self.current_user, contact, self.server_url)
            self.chat_tabs.addTab(chat_widget, f"💬 {contact['username']}")
            self.chat_tabs.setCurrentIndex(self.chat_tabs.count() - 1)
            
            # Очищаем счетчик непрочитанных
            if contact["id"] in self.unread_messages:
                del self.unread_messages[contact["id"]]
                self.update_contacts_list()
                
        except Exception as e:
            print(f"❌ Error opening chat: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть чат: {str(e)}")
            
    def close_chat_tab(self, index):
        """Закрытие вкладки чата"""
        widget = self.chat_tabs.widget(index)
        
        # Закрываем WebSocket соединение если есть
        if hasattr(widget, 'websocket'):
            try:
                widget.websocket.disconnect()
            except:
                pass
        
        self.chat_tabs.removeTab(index)
        
    def logout(self):
        """Выход из системы"""
        try:
            # Отправляем запрос на выход
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(
                f"{self.server_url}/auth/logout",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ User {self.current_user['id']} logged out successfully")
            else:
                print(f"⚠️ Logout API error: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️ Cannot connect to server during logout")
        except Exception as e:
            print(f"⚠️ Logout error: {e}")
        finally:
            # Выходим из сессии
            self.auth_manager.logout()
            
            # Закрываем все WebSocket соединения
            for i in range(self.chat_tabs.count()):
                widget = self.chat_tabs.widget(i)
                if hasattr(widget, 'websocket'):
                    try:
                        widget.websocket.disconnect()
                    except:
                        pass
            
            # Закрываем окно
            self.close()
            
    def change_server(self):
        """Смена сервера"""
        reply = QMessageBox.question(
            self, "Сменить сервер",
            "Вы уверены, что хотите сменить сервер?\nТекущая сессия будет завершена.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Закрываем все соединения
            self.logout()
            
            # Перезапускаем приложение
            QApplication.exit(100)  # Специальный код для перезапуска
            
    def show_settings(self):
        """Показ настроек"""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec_()
        
    def show_about(self):
        """Показ информации о программе"""
        about_text = f"""
        <h2>{APP_NAME}</h2>
        <p><b>Версия:</b> {APP_VERSION}</p>
        <p>Быстрый и безопасный мессенджер для локальной сети.</p>
        <p><b>Текущий сервер:</b> {self.server_url}</p>
        <p><b>Пользователь:</b> {self.current_user.get('username', 'Неизвестно')}</p>
        <hr>
        <p>© 2024 Local Messenger Team</p>
        <p>🐱 meow miaw :D</p>
        """
        
        QMessageBox.about(self, f"О программе {APP_NAME}", about_text)
        
    def show_help(self):
        """Показ справки"""
        help_text = """
        <h2>Справка по Local Messenger</h2>
        
        <h3>Основные функции:</h3>
        <ul>
            <li><b>Обмен сообщениями:</b> Отправка текстовых сообщений и изображений</li>
            <li><b>Групповые чаты:</b> Создание групповых бесед (в разработке)</li>
            <li><b>Статусы:</b> Отображение статуса онлайн/оффлайн пользователей</li>
            <li><b>Уведомления:</b> Звуковые и системные уведомления</li>
        </ul>
        
        <h3>Горячие клавиши:</h3>
        <ul>
            <li><b>Ctrl+N:</b> Новый чат</li>
            <li><b>Ctrl+F:</b> Поиск</li>
            <li><b>Ctrl+Q:</b> Выход</li>
            <li><b>Enter:</b> Отправить сообщение</li>
            <li><b>Ctrl+Enter:</b> Новая строка в сообщении</li>
        </ul>
        
        <h3>Советы:</h3>
        <ul>
            <li>Дважды кликните по контакту для быстрого открытия чата</li>
            <li>Используйте системный трей для быстрого доступа</li>
            <li>Вы можете менять серверы не выходя из приложения</li>
            <li>Настройки сохраняются автоматически</li>
        </ul>
        """
        
        QMessageBox.information(self, "Справка", help_text)
        
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        try:
            # Пытаемся отправить запрос на выход
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(
                f"{self.server_url}/auth/logout",
                headers=headers,
                timeout=2
            )
        except:
            pass  # Игнорируем ошибки при закрытии
        
        # Закрываем все WebSocket соединения
        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if hasattr(widget, 'websocket'):
                try:
                    widget.websocket.disconnect()
                except:
                    pass
        
        # Скрываем иконку в трее
        if self.system_tray:
            self.system_tray.hide()
        
        event.accept()


if __name__ == "__main__":
    # Тестирование
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Тестовые данные
    test_user = {
        "id": 1,
        "username": "test_user",
        "is_online": True
    }
    
    window = MainWindow("test_token", test_user, "http://127.0.0.1:8000")
    window.show()
    
    sys.exit(app.exec_())