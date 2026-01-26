"""
Диалог настроек клиента.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QWidget, QLabel, QComboBox, QCheckBox, QPushButton,
                            QGroupBox, QFormLayout, QSpinBox, QLineEdit, 
                            QMessageBox, QListWidget, QListWidgetItem, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QFont

from utils.auth_manager import get_auth_manager
from utils.theme_manager import get_theme_manager, init_theme
from utils.notifications import get_notification_manager


class SettingsDialog(QDialog):
    """
    Диалог настроек приложения.
    """
    
    settings_changed = pyqtSignal()  # Сигнал при изменении настроек
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.auth_manager = get_auth_manager()
        self.theme_manager = get_theme_manager()
        self.notification_manager = get_notification_manager()
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("⚙️ Настройки")
        self.setGeometry(400, 300, 700, 600)
        self.setMinimumSize(650, 550)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("Настройки приложения")
        title_font = self.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1976d2; padding: 10px 0;")
        main_layout.addWidget(title_label)
        
        # Создаем вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #1976d2;
            }
            QTabBar::tab:hover {
                background-color: #e8e8e8;
            }
        """)
        
        # Вкладка "Основные"
        general_tab = self.create_general_tab()
        self.tab_widget.addTab(general_tab, "📋 Основные")
        
        # Вкладка "Оформление"
        appearance_tab = self.create_appearance_tab()
        self.tab_widget.addTab(appearance_tab, "🎨 Оформление")
        
        # Вкладка "Уведомления"
        notifications_tab = self.create_notifications_tab()
        self.tab_widget.addTab(notifications_tab, "🔔 Уведомления")
        
        # Вкладка "Сеть"
        network_tab = self.create_network_tab()
        self.tab_widget.addTab(network_tab, "🌐 Сеть")
        
        main_layout.addWidget(self.tab_widget)
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Кнопка "Сброс"
        self.reset_btn = QPushButton("🔄 Сбросить")
        self.reset_btn.clicked.connect(self.reset_settings)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        button_layout.addWidget(self.reset_btn)
        
        # Растягивающийся спейсер
        button_layout.addStretch()
        
        # Кнопка "Отмена"
        self.cancel_btn = QPushButton("❌ Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        # Кнопка "Сохранить"
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setDefault(True)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def create_general_tab(self):
        """Создание вкладки основных настроек"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Группа "Запуск"
        startup_group = QGroupBox("🚀 Запуск")
        startup_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        startup_layout = QVBoxLayout()
        
        self.auto_login_checkbox = QCheckBox("Автоматический вход")
        self.auto_login_checkbox.setToolTip("Автоматически входить при запуске приложения")
        startup_layout.addWidget(self.auto_login_checkbox)
        
        self.auto_start_checkbox = QCheckBox("Запускать с системой")
        self.auto_start_checkbox.setToolTip("Автозапуск приложения при запуске Windows")
        startup_layout.addWidget(self.auto_start_checkbox)
        
        self.minimize_to_tray_checkbox = QCheckBox("Сворачивать в системный трей")
        self.minimize_to_tray_checkbox.setToolTip("При закрытии сворачивать в трей вместо выхода")
        startup_layout.addWidget(self.minimize_to_tray_checkbox)
        
        self.remember_me_checkbox = QCheckBox("Запоминать меня")
        self.remember_me_checkbox.setToolTip("Сохранять данные для входа")
        startup_layout.addWidget(self.remember_me_checkbox)
        
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        # Группа "Интерфейс"
        interface_group = QGroupBox("💻 Интерфейс")
        interface_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        interface_layout = QFormLayout()
        interface_layout.setSpacing(10)
        
        # Язык
        self.language_combo = QComboBox()
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("English", "en")
        interface_layout.addRow("Язык:", self.language_combo)
        
        # Максимальное количество сообщений
        self.message_limit_spinbox = QSpinBox()
        self.message_limit_spinbox.setRange(50, 5000)
        self.message_limit_spinbox.setValue(1000)
        self.message_limit_spinbox.setSuffix(" сообщений")
        interface_layout.addRow("Лимит сообщений:", self.message_limit_spinbox)
        
        # Показывать время сообщений
        self.show_timestamps_checkbox = QCheckBox("Показывать время сообщений")
        interface_layout.addRow("", self.show_timestamps_checkbox)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # Группа "Файлы"
        files_group = QGroupBox("📁 Файлы")
        files_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        files_layout = QFormLayout()
        files_layout.setSpacing(10)
        
        # Максимальный размер файла
        self.max_file_size_spinbox = QSpinBox()
        self.max_file_size_spinbox.setRange(1, 100)
        self.max_file_size_spinbox.setValue(10)
        self.max_file_size_spinbox.setSuffix(" МБ")
        files_layout.addRow("Макс. размер файла:", self.max_file_size_spinbox)
        
        # Автосохранение
        self.auto_save_checkbox = QCheckBox("Автоматически сохранять файлы")
        files_layout.addRow("", self.auto_save_checkbox)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def create_appearance_tab(self):
        """Создание вкладки оформления"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Группа "Тема"
        theme_group = QGroupBox("🎨 Тема оформления")
        theme_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        theme_layout = QVBoxLayout()
        
        # Список тем
        self.theme_list = QListWidget()
        self.theme_list.setMinimumHeight(200)
        self.theme_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        theme_layout.addWidget(self.theme_list)
        
        # Предпросмотр темы
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Предпросмотр:")
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)
        
        preview_layout.addStretch()
        
        # Кнопки управления темами
        btn_layout = QHBoxLayout()
        
        self.refresh_themes_btn = QPushButton("🔄 Обновить")
        self.refresh_themes_btn.clicked.connect(self.refresh_themes)
        self.refresh_themes_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #ccc;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        btn_layout.addWidget(self.refresh_themes_btn)
        
        self.delete_theme_btn = QPushButton("🗑️ Удалить")
        self.delete_theme_btn.clicked.connect(self.delete_selected_theme)
        self.delete_theme_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #ccc;
                background-color: white;
                color: #f44336;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
        """)
        btn_layout.addWidget(self.delete_theme_btn)
        
        preview_layout.addLayout(btn_layout)
        theme_layout.addLayout(preview_layout)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Группа "Дополнительно"
        advanced_group = QGroupBox("🔧 Дополнительно")
        advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        advanced_layout = QFormLayout()
        advanced_layout.setSpacing(10)
        
        # Размер шрифта
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItem("Маленький", "small")
        self.font_size_combo.addItem("Средний", "medium")
        self.font_size_combo.addItem("Большой", "large")
        advanced_layout.addRow("Размер шрифта:", self.font_size_combo)
        
        # Сглаживание шрифтов
        self.font_smoothing_checkbox = QCheckBox("Сглаживание шрифтов")
        advanced_layout.addRow("", self.font_smoothing_checkbox)
        
        # Анимации
        self.animations_checkbox = QCheckBox("Включить анимации")
        advanced_layout.addRow("", self.animations_checkbox)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def create_notifications_tab(self):
        """Создание вкладки уведомлений"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Группа "Общие настройки"
        general_group = QGroupBox("🔔 Общие настройки")
        general_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        general_layout = QVBoxLayout()
        
        self.notifications_enabled_checkbox = QCheckBox("Включить уведомления")
        self.notifications_enabled_checkbox.stateChanged.connect(self.toggle_notification_settings)
        general_layout.addWidget(self.notifications_enabled_checkbox)
        
        self.sound_notifications_checkbox = QCheckBox("Звуковые уведомления")
        general_layout.addWidget(self.sound_notifications_checkbox)
        
        self.tray_notifications_checkbox = QCheckBox("Уведомления в системном трее")
        general_layout.addWidget(self.tray_notifications_checkbox)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Группа "Типы уведомлений"
        types_group = QGroupBox("📨 Типы уведомлений")
        types_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        types_layout = QVBoxLayout()
        
        self.message_notifications_checkbox = QCheckBox("Новые сообщения")
        types_layout.addWidget(self.message_notifications_checkbox)
        
        self.file_notifications_checkbox = QCheckBox("Полученные файлы")
        types_layout.addWidget(self.file_notifications_checkbox)
        
        self.call_notifications_checkbox = QCheckBox("Входящие звонки")
        types_layout.addWidget(self.call_notifications_checkbox)
        
        self.error_notifications_checkbox = QCheckBox("Ошибки")
        types_layout.addWidget(self.error_notifications_checkbox)
        
        types_group.setLayout(types_layout)
        layout.addWidget(types_group)
        
        # Группа "Дополнительно"
        notification_advanced_group = QGroupBox("⚙️ Дополнительно")
        notification_advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        notification_advanced_layout = QFormLayout()
        notification_advanced_layout.setSpacing(10)
        
        # Длительность уведомлений
        self.notification_duration_spinbox = QSpinBox()
        self.notification_duration_spinbox.setRange(1, 30)
        self.notification_duration_spinbox.setValue(5)
        self.notification_duration_spinbox.setSuffix(" секунд")
        notification_advanced_layout.addRow("Длительность:", self.notification_duration_spinbox)
        
        # Тестовое уведомление
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        
        self.test_notification_btn = QPushButton("Тестовое уведомление")
        self.test_notification_btn.clicked.connect(self.test_notification)
        self.test_notification_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        test_layout.addWidget(self.test_notification_btn)
        
        notification_advanced_layout.addRow("", test_layout)
        
        notification_advanced_group.setLayout(notification_advanced_layout)
        layout.addWidget(notification_advanced_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def create_network_tab(self):
        """Создание вкладки сетевых настроек"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Группа "Соединение"
        connection_group = QGroupBox("🌐 Соединение")
        connection_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        connection_layout = QFormLayout()
        connection_layout.setSpacing(10)
        
        # Таймаут соединения
        self.connection_timeout_spinbox = QSpinBox()
        self.connection_timeout_spinbox.setRange(1, 60)
        self.connection_timeout_spinbox.setValue(10)
        self.connection_timeout_spinbox.setSuffix(" секунд")
        connection_layout.addRow("Таймаут соединения:", self.connection_timeout_spinbox)
        
        # Количество попыток переподключения
        self.reconnect_attempts_spinbox = QSpinBox()
        self.reconnect_attempts_spinbox.setRange(1, 10)
        self.reconnect_attempts_spinbox.setValue(3)
        self.reconnect_attempts_spinbox.setSuffix(" попыток")
        connection_layout.addRow("Попытки переподключения:", self.reconnect_attempts_spinbox)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # Группа "Прокси"
        proxy_group = QGroupBox("🔌 Прокси-сервер")
        proxy_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        proxy_layout = QFormLayout()
        proxy_layout.setSpacing(10)
        
        # Использовать прокси
        self.use_proxy_checkbox = QCheckBox("Использовать прокси-сервер")
        self.use_proxy_checkbox.stateChanged.connect(self.toggle_proxy_settings)
        proxy_layout.addRow("", self.use_proxy_checkbox)
        
        # Адрес прокси
        self.proxy_address_input = QLineEdit()
        self.proxy_address_input.setPlaceholderText("proxy.example.com:8080")
        proxy_layout.addRow("Адрес:", self.proxy_address_input)
        
        # Логин
        self.proxy_username_input = QLineEdit()
        self.proxy_username_input.setPlaceholderText("логин")
        proxy_layout.addRow("Логин:", self.proxy_username_input)
        
        # Пароль
        self.proxy_password_input = QLineEdit()
        self.proxy_password_input.setPlaceholderText("пароль")
        self.proxy_password_input.setEchoMode(QLineEdit.Password)
        proxy_layout.addRow("Пароль:", self.proxy_password_input)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        # Группа "Дополнительно"
        network_advanced_group = QGroupBox("🔧 Дополнительно")
        network_advanced_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        network_advanced_layout = QFormLayout()
        network_advanced_layout.setSpacing(10)
        
        # Использовать UDP broadcast
        self.use_broadcast_checkbox = QCheckBox("Использовать UDP broadcast")
        network_advanced_layout.addRow("", self.use_broadcast_checkbox)
        
        # Автоматический поиск серверов
        self.auto_discovery_checkbox = QCheckBox("Автоматический поиск серверов")
        network_advanced_layout.addRow("", self.auto_discovery_checkbox)
        
        network_advanced_group.setLayout(network_advanced_layout)
        layout.addWidget(network_advanced_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def load_settings(self):
        """Загрузка настроек"""
        try:
            # Основные настройки
            self.auto_login_checkbox.setChecked(
                self.auth_manager.get_setting('auto_login', False)
            )
            self.auto_start_checkbox.setChecked(
                self.auth_manager.get_setting('auto_start', False)
            )
            self.minimize_to_tray_checkbox.setChecked(
                self.auth_manager.get_setting('minimize_to_tray', True)
            )
            self.remember_me_checkbox.setChecked(
                self.auth_manager.get_setting('remember_me', False)
            )
            
            # Интерфейс
            language = self.auth_manager.get_setting('language', 'ru')
            index = self.language_combo.findData(language)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
            
            self.message_limit_spinbox.setValue(
                self.auth_manager.get_setting('message_limit', 1000)
            )
            self.show_timestamps_checkbox.setChecked(
                self.auth_manager.get_setting('show_timestamps', True)
            )
            
            # Файлы
            self.max_file_size_spinbox.setValue(
                self.auth_manager.get_setting('max_file_size', 10)
            )
            self.auto_save_checkbox.setChecked(
                self.auth_manager.get_setting('auto_save_files', False)
            )
            
            # Темы
            self.load_themes()
            
            # Размер шрифта
            font_size = self.auth_manager.get_setting('font_size', 'medium')
            index = self.font_size_combo.findData(font_size)
            if index >= 0:
                self.font_size_combo.setCurrentIndex(index)
            
            self.font_smoothing_checkbox.setChecked(
                self.auth_manager.get_setting('font_smoothing', True)
            )
            self.animations_checkbox.setChecked(
                self.auth_manager.get_setting('animations', True)
            )
            
            # Уведомления
            self.notifications_enabled_checkbox.setChecked(
                self.auth_manager.get_setting('notifications', True)
            )
            self.sound_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('sound_notifications', True)
            )
            self.tray_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('tray_notifications', True)
            )
            
            self.message_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('notify_messages', True)
            )
            self.file_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('notify_files', True)
            )
            self.call_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('notify_calls', True)
            )
            self.error_notifications_checkbox.setChecked(
                self.auth_manager.get_setting('notify_errors', True)
            )
            
            self.notification_duration_spinbox.setValue(
                self.auth_manager.get_setting('notification_duration', 5)
            )
            
            # Включаем/отключаем настройки уведомлений
            self.toggle_notification_settings()
            
            # Сеть
            self.connection_timeout_spinbox.setValue(
                self.auth_manager.get_setting('connection_timeout', 10)
            )
            self.reconnect_attempts_spinbox.setValue(
                self.auth_manager.get_setting('reconnect_attempts', 3)
            )
            
            self.use_proxy_checkbox.setChecked(
                self.auth_manager.get_setting('use_proxy', False)
            )
            self.proxy_address_input.setText(
                self.auth_manager.get_setting('proxy_address', '')
            )
            self.proxy_username_input.setText(
                self.auth_manager.get_setting('proxy_username', '')
            )
            self.proxy_password_input.setText(
                self.auth_manager.get_setting('proxy_password', '')
            )
            
            self.use_broadcast_checkbox.setChecked(
                self.auth_manager.get_setting('use_broadcast', True)
            )
            self.auto_discovery_checkbox.setChecked(
                self.auth_manager.get_setting('auto_discovery', True)
            )
            
            # Включаем/отключаем настройки прокси
            self.toggle_proxy_settings()
            
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            
    def load_themes(self):
        """Загрузка списка тем"""
        self.theme_list.clear()
        
        themes = self.theme_manager.get_available_themes()
        current_theme = self.theme_manager.get_current_theme_info()
        
        for theme in themes:
            item_text = f"{theme['name']} ({theme['type']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, theme['id'])
            
            # Выделяем текущую тему
            if theme['id'] == current_theme['id']:
                item.setBackground(QColor(227, 242, 253))
                item.setForeground(QColor(25, 118, 210))
                item.setFont(QFont(self.font().family(), self.font().pointSize(), QFont.Bold))
                self.theme_list.setCurrentItem(item)
            
            self.theme_list.addItem(item)
            
    def refresh_themes(self):
        """Обновление списка тем"""
        self.theme_manager.load_themes()
        self.load_themes()
        
    def delete_selected_theme(self):
        """Удаление выбранной темы"""
        current_item = self.theme_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Ошибка", "Выберите тему для удаления")
            return
        
        theme_id = current_item.data(Qt.UserRole)
        theme_info = None
        
        # Находим информацию о теме
        themes = self.theme_manager.get_available_themes()
        for theme in themes:
            if theme['id'] == theme_id:
                theme_info = theme
                break
        
        if not theme_info:
            return
        
        # Нельзя удалять встроенные темы
        if theme_info['type'] == 'builtin':
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить встроенную тему")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self, "Удаление темы",
            f"Вы уверены, что хотите удалить тему '{theme_info['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.theme_manager.delete_custom_theme(theme_id)
            if success:
                QMessageBox.information(self, "Успех", "Тема успешно удалена")
                self.load_themes()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить тему")
                
    def toggle_notification_settings(self):
        """Включение/отключение настроек уведомлений"""
        enabled = self.notifications_enabled_checkbox.isChecked()
        
        self.sound_notifications_checkbox.setEnabled(enabled)
        self.tray_notifications_checkbox.setEnabled(enabled)
        self.message_notifications_checkbox.setEnabled(enabled)
        self.file_notifications_checkbox.setEnabled(enabled)
        self.call_notifications_checkbox.setEnabled(enabled)
        self.error_notifications_checkbox.setEnabled(enabled)
        self.notification_duration_spinbox.setEnabled(enabled)
        self.test_notification_btn.setEnabled(enabled)
        
    def toggle_proxy_settings(self):
        """Включение/отключение настроек прокси"""
        enabled = self.use_proxy_checkbox.isChecked()
        
        self.proxy_address_input.setEnabled(enabled)
        self.proxy_username_input.setEnabled(enabled)
        self.proxy_password_input.setEnabled(enabled)
        
    def test_notification(self):
        """Тестовое уведомление"""
        self.notification_manager.notify_new_message(
            "Тестовый пользователь",
            "Это тестовое уведомление!",
            is_important=False
        )
        
    def save_settings(self):
        """Сохранение настроек"""
        try:
            # Основные настройки
            self.auth_manager.set_setting('auto_login', 
                self.auto_login_checkbox.isChecked())
            self.auth_manager.set_setting('auto_start',
                self.auto_start_checkbox.isChecked())
            self.auth_manager.set_setting('minimize_to_tray',
                self.minimize_to_tray_checkbox.isChecked())
            self.auth_manager.set_setting('remember_me',
                self.remember_me_checkbox.isChecked())
            
            # Интерфейс
            self.auth_manager.set_setting('language',
                self.language_combo.currentData())
            self.auth_manager.set_setting('message_limit',
                self.message_limit_spinbox.value())
            self.auth_manager.set_setting('show_timestamps',
                self.show_timestamps_checkbox.isChecked())
            
            # Файлы
            self.auth_manager.set_setting('max_file_size',
                self.max_file_size_spinbox.value())
            self.auth_manager.set_setting('auto_save_files',
                self.auto_save_checkbox.isChecked())
            
            # Тема
            current_item = self.theme_list.currentItem()
            if current_item:
                theme_id = current_item.data(Qt.UserRole)
                self.theme_manager.set_theme(theme_id)
            
            # Размер шрифта
            self.auth_manager.set_setting('font_size',
                self.font_size_combo.currentData())
            self.auth_manager.set_setting('font_smoothing',
                self.font_smoothing_checkbox.isChecked())
            self.auth_manager.set_setting('animations',
                self.animations_checkbox.isChecked())
            
            # Уведомления
            self.auth_manager.set_setting('notifications',
                self.notifications_enabled_checkbox.isChecked())
            self.auth_manager.set_setting('sound_notifications',
                self.sound_notifications_checkbox.isChecked())
            self.auth_manager.set_setting('tray_notifications',
                self.tray_notifications_checkbox.isChecked())
            
            self.auth_manager.set_setting('notify_messages',
                self.message_notifications_checkbox.isChecked())
            self.auth_manager.set_setting('notify_files',
                self.file_notifications_checkbox.isChecked())
            self.auth_manager.set_setting('notify_calls',
                self.call_notifications_checkbox.isChecked())
            self.auth_manager.set_setting('notify_errors',
                self.error_notifications_checkbox.isChecked())
            
            self.auth_manager.set_setting('notification_duration',
                self.notification_duration_spinbox.value())
            
            # Обновляем менеджер уведомлений
            self.notification_manager.enable_notifications(
                self.notifications_enabled_checkbox.isChecked()
            )
            self.notification_manager.enable_sound(
                self.sound_notifications_checkbox.isChecked()
            )
            
            # Сеть
            self.auth_manager.set_setting('connection_timeout',
                self.connection_timeout_spinbox.value())
            self.auth_manager.set_setting('reconnect_attempts',
                self.reconnect_attempts_spinbox.value())
            
            self.auth_manager.set_setting('use_proxy',
                self.use_proxy_checkbox.isChecked())
            self.auth_manager.set_setting('proxy_address',
                self.proxy_address_input.text())
            self.auth_manager.set_setting('proxy_username',
                self.proxy_username_input.text())
            self.auth_manager.set_setting('proxy_password',
                self.proxy_password_input.text())
            
            self.auth_manager.set_setting('use_broadcast',
                self.use_broadcast_checkbox.isChecked())
            self.auth_manager.set_setting('auto_discovery',
                self.auto_discovery_checkbox.isChecked())
            
            # Сохраняем настройки в файл
            self.auth_manager.save_settings()
            
            # Отправляем сигнал
            self.settings_changed.emit()
            
            QMessageBox.information(self, "Успех", "Настройки сохранены")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{str(e)}")
            
    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(
            self, "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?\n\n"
            "Это действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.auth_manager.clear_all_data()
            self.load_settings()
            QMessageBox.information(self, "Успех", "Настройки сброшены к значениям по умолчанию")


if __name__ == "__main__":
    # Тестирование диалога настроек
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Инициализируем тему
    init_theme()
    
    dialog = SettingsDialog()
    
    def on_settings_changed():
        print("Настройки изменены")
    
    dialog.settings_changed.connect(on_settings_changed)
    
    if dialog.exec_() == QDialog.Accepted:
        print("Настройки сохранены")
    else:
        print("Изменения отменены")
    
    sys.exit(0)