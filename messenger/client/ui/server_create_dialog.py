"""
Диалог создания нового сервера мессенджера.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QSpinBox, QCheckBox,
    QPushButton, QLabel, QMessageBox, QGroupBox,
    QTabWidget, QWidget, QGridLayout, QComboBox,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator, QIcon
import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ServerCreateDialog(QDialog):
    """
    Диалог для создания и настройки нового сервера.
    """
    
    server_created = pyqtSignal(dict)  # Сигнал с данными созданного сервера
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.server_data = {}
        self.init_ui()
        self.load_network_interfaces()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Создание нового сервера")
        self.setGeometry(400, 300, 650, 750)
        self.setMinimumSize(600, 700)
        
        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("🎯 Создание нового сервера мессенджера")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1976d2; padding: 5px;")
        main_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Настройте параметры сервера для работы в локальной сети")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-style: italic; padding-bottom: 10px;")
        main_layout.addWidget(subtitle_label)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #ddd; margin: 5px 0;")
        main_layout.addWidget(separator)
        
        # Создаем вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
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
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e8e8e8;
            }
        """)
        
        # Основные настройки
        basic_tab = self.create_basic_tab()
        self.tab_widget.addTab(basic_tab, "📋 Основные")
        
        # Расширенные настройки
        advanced_tab = self.create_advanced_tab()
        self.tab_widget.addTab(advanced_tab, "⚙️ Расширенные")
        
        main_layout.addWidget(self.tab_widget)
        
        # Информационная панель
        info_panel = self.create_info_panel()
        main_layout.addWidget(info_panel)
        
        # Панель кнопок
        button_panel = self.create_button_panel()
        main_layout.addWidget(button_panel)
        
        self.setLayout(main_layout)
        
        # Валидация
        self.validate_inputs()
        
    def create_basic_tab(self) -> QWidget:
        """Создание вкладки с основными настройками"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Группа информации о сервере
        info_group = QGroupBox("📝 Информация о сервере")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        info_layout = QFormLayout()
        info_layout.setSpacing(10)
        
        # Название сервера
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название сервера")
        self.name_input.textChanged.connect(self.validate_inputs)
        info_layout.addRow("Название сервера:", self.name_input)
        
        # Описание
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Введите описание сервера (необязательно)")
        info_layout.addRow("Описание:", self.description_input)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Группа сетевых настроек
        network_group = QGroupBox("🌐 Сетевые настройки")
        network_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        network_layout = QFormLayout()
        network_layout.setSpacing(10)
        
        # Выбор сетевого интерфейса
        self.interface_combo = QComboBox()
        self.interface_combo.currentIndexChanged.connect(self.on_interface_changed)
        network_layout.addRow("Сетевой интерфейс:", self.interface_combo)
        
        # IP адрес
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("0.0.0.0 (все интерфейсы)")
        self.ip_input.textChanged.connect(self.validate_inputs)
        network_layout.addRow("IP адрес:", self.ip_input)
        
        # Порт сервера
        port_layout = QHBoxLayout()
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8000)
        self.port_input.valueChanged.connect(self.validate_inputs)
        port_layout.addWidget(self.port_input)
        
        self.test_port_btn = QPushButton("Проверить порт")
        self.test_port_btn.setObjectName("testBtn")
        self.test_port_btn.clicked.connect(self.test_port)
        self.test_port_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        port_layout.addWidget(self.test_port_btn)
        
        network_layout.addRow("Порт сервера:", port_layout)
        
        # Порт для broadcast
        self.broadcast_port_input = QSpinBox()
        self.broadcast_port_input.setRange(1024, 65535)
        self.broadcast_port_input.setValue(37020)
        network_layout.addRow("Порт broadcast:", self.broadcast_port_input)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # Группа пароля
        password_group = QGroupBox("🔐 Защита паролем")
        password_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        password_layout = QVBoxLayout()
        password_layout.setSpacing(10)
        
        # Чекбокс защиты паролем
        self.password_checkbox = QCheckBox("Защитить сервер паролем")
        self.password_checkbox.stateChanged.connect(self.toggle_password_fields)
        password_layout.addWidget(self.password_checkbox)
        
        # Поля пароля (скрыты по умолчанию)
        password_fields_layout = QFormLayout()
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setEnabled(False)
        self.password_input.textChanged.connect(self.validate_inputs)
        self.password_input.setPlaceholderText("Введите пароль (минимум 4 символа)")
        password_fields_layout.addRow("Пароль:", self.password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setEnabled(False)
        self.confirm_password_input.textChanged.connect(self.validate_inputs)
        self.confirm_password_input.setPlaceholderText("Повторите пароль")
        password_fields_layout.addRow("Подтверждение:", self.confirm_password_input)
        
        password_layout.addLayout(password_fields_layout)
        
        # Подсказка о пароле
        password_hint = QLabel("💡 Пароль потребуется для запуска сервера другими пользователями")
        password_hint.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background-color: #f9f9f9; border-radius: 4px;")
        password_hint.setWordWrap(True)
        password_layout.addWidget(password_hint)
        
        password_group.setLayout(password_layout)
        layout.addWidget(password_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def create_advanced_tab(self) -> QWidget:
        """Создание вкладки с расширенными настройками"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Группа ограничений
        limits_group = QGroupBox("📊 Ограничения")
        limits_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        limits_layout = QFormLayout()
        limits_layout.setSpacing(10)
        
        # Максимальное количество пользователей
        self.max_users_input = QSpinBox()
        self.max_users_input.setRange(1, 1000)
        self.max_users_input.setValue(50)
        limits_layout.addRow("Макс. пользователей:", self.max_users_input)
        
        # Автозапуск
        self.auto_start_checkbox = QCheckBox("Автозапуск при запуске клиента")
        limits_layout.addRow(self.auto_start_checkbox)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # Группа дополнительных настроек
        extra_group = QGroupBox("🔧 Дополнительно")
        extra_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
            }
        """)
        extra_layout = QFormLayout()
        extra_layout.setSpacing(10)
        
        # Сохранить конфигурацию
        self.save_config_checkbox = QCheckBox("Сохранить конфигурацию сервера")
        self.save_config_checkbox.setChecked(True)
        extra_layout.addRow(self.save_config_checkbox)
        
        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
        
    def create_info_panel(self) -> QWidget:
        """Создание информационной панели"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        
        info_title = QLabel("💡 Важная информация")
        info_title.setStyleSheet("font-weight: bold; color: #1976d2; font-size: 13px;")
        layout.addWidget(info_title)
        
        info_text = QLabel(
            "• Сервер будет доступен другим пользователям в локальной сети\n"
            "• Порт должен быть свободен для успешного запуска\n"
            "• При защите паролем другие пользователи смогут запустить сервер,\n"
            "  только зная правильный пароль\n"
            "• Broadcast порт используется для обнаружения сервера в сети\n"
            "• Для подключения других пользователей сообщите им IP и порт сервера"
        )
        info_text.setStyleSheet("color: #555; font-size: 11px; line-height: 1.4;")
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        panel.setLayout(layout)
        return panel
        
    def create_button_panel(self) -> QWidget:
        """Создание панели кнопок"""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # Кнопка отмены
        self.cancel_btn = QPushButton("❌ Отмена")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(self.cancel_btn)
        
        # Растягивающийся спейсер
        layout.addStretch()
        
        # Кнопка создания
        self.create_btn = QPushButton("🚀 Создать сервер")
        self.create_btn.setObjectName("createBtn")
        self.create_btn.clicked.connect(self.create_server)
        self.create_btn.setEnabled(False)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 32px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                cursor: not-allowed;
            }
        """)
        layout.addWidget(self.create_btn)
        
        panel.setLayout(layout)
        return panel
        
    def load_network_interfaces(self):
        """Загрузка доступных сетевых интерфейсов"""
        try:
            # Получаем локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Добавляем опции
            self.interface_combo.addItem(f"Все интерфейсы (0.0.0.0)", "0.0.0.0")
            self.interface_combo.addItem(f"Локальный хост (127.0.0.1)", "127.0.0.1")
            self.interface_combo.addItem(f"Текущий IP ({local_ip})", local_ip)
            
            # Устанавливаем текущий IP по умолчанию
            self.ip_input.setText(local_ip)
            
        except Exception as e:
            logger.error(f"Ошибка получения сетевых интерфейсов: {e}")
            self.interface_combo.addItem("Все интерфейсы (0.0.0.0)", "0.0.0.0")
            self.ip_input.setText("127.0.0.1")
            
    def on_interface_changed(self, index):
        """Обработка изменения выбранного интерфейса"""
        if index >= 0:
            ip = self.interface_combo.itemData(index)
            if ip:
                self.ip_input.setText(ip)
                
    def toggle_password_fields(self, state):
        """Включение/отключение полей пароля"""
        enabled = state == Qt.Checked
        self.password_input.setEnabled(enabled)
        self.confirm_password_input.setEnabled(enabled)
        
        if not enabled:
            self.password_input.clear()
            self.confirm_password_input.clear()
            
        self.validate_inputs()
            
    def test_port(self):
        """Проверка доступности порта"""
        ip = self.ip_input.text() or "0.0.0.0"
        port = self.port_input.value()
        
        try:
            # Пробуем забиндиться на порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip if ip != "0.0.0.0" else "127.0.0.1", port))
            sock.close()
            
            if result == 0:
                QMessageBox.warning(self, "Порт занят", 
                                  f"⚠️ Порт {port} уже используется.\n\n"
                                  f"Пожалуйста, выберите другой порт.")
                self.port_input.setFocus()
                self.port_input.selectAll()
                return False
            else:
                QMessageBox.information(self, "Порт свободен", 
                                      f"✅ Порт {port} свободен и может быть использован.")
                return True
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                               f"❌ Не удалось проверить порт:\n\n{str(e)}")
            return False
            
    def validate_inputs(self):
        """Валидация введенных данных"""
        # Проверяем название
        name = self.name_input.text().strip()
        name_valid = bool(name)
        
        # Проверяем IP
        ip = self.ip_input.text().strip()
        ip_valid = True
        
        if ip:
            try:
                socket.inet_aton(ip)
                ip_valid = True
            except socket.error:
                ip_valid = False
        
        # Проверяем пароль если требуется
        password_valid = True
        if self.password_checkbox.isChecked():
            password = self.password_input.text()
            confirm_password = self.confirm_password_input.text()
            
            if password:
                password_valid = len(password) >= 4 and password == confirm_password
            else:
                password_valid = False
        
        # Активируем кнопку создания если все валидно
        self.create_btn.setEnabled(name_valid and ip_valid and password_valid)
        
        # Меняем цвет рамки невалидных полей
        name_style = "border: 2px solid #f44336;" if not name_valid and name else ""
        self.name_input.setStyleSheet(name_style)
        
        ip_style = "border: 2px solid #f44336;" if not ip_valid and ip else ""
        self.ip_input.setStyleSheet(ip_style)
        
        if self.password_checkbox.isChecked():
            password_style = "border: 2px solid #f44336;" if not password_valid and password else ""
            self.password_input.setStyleSheet(password_style)
            self.confirm_password_input.setStyleSheet(password_style)
        
    def create_server(self):
        """Создание сервера"""
        try:
            # Проверяем порт
            if not self.test_port():
                return
            
            # Получаем данные из формы
            server_data = {
                "name": self.name_input.text().strip(),
                "description": self.description_input.toPlainText().strip(),
                "ip": self.ip_input.text().strip() or "0.0.0.0",
                "port": self.port_input.value(),
                "broadcast_port": self.broadcast_port_input.value(),
                "max_users": self.max_users_input.value(),
                "password_protected": self.password_checkbox.isChecked(),
                "password": self.password_input.text() if self.password_checkbox.isChecked() else None,
                "auto_start": self.auto_start_checkbox.isChecked(),
                "save_config": self.save_config_checkbox.isChecked()
            }
            
            # Валидируем пароль
            if server_data["password_protected"] and server_data["password"]:
                if len(server_data["password"]) < 4:
                    QMessageBox.warning(self, "Ошибка", 
                                      "❌ Пароль должен быть не менее 4 символов")
                    self.password_input.setFocus()
                    self.password_input.selectAll()
                    return
            
            # Подтверждение создания
            reply = QMessageBox.question(
                self, "Подтверждение",
                f"Создать сервер '{server_data['name']}'?\n\n"
                f"Адрес: {server_data['ip']}:{server_data['port']}\n"
                f"Защита паролем: {'Да' if server_data['password_protected'] else 'Нет'}",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Сохраняем данные
            self.server_data = server_data
            
            # Отправляем сигнал
            self.server_created.emit(server_data)
            
            # Закрываем диалог
            self.accept()
            
        except Exception as e:
            logger.error(f"Ошибка создания сервера: {e}")
            QMessageBox.critical(self, "Ошибка", 
                               f"❌ Не удалось создать сервер:\n\n{str(e)}")
            
    def get_server_config(self) -> dict:
        """Получение конфигурации сервера"""
        return self.server_data


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль
    app.setStyle("Fusion")
    
    dialog = ServerCreateDialog()
    
    def on_server_created(server_data):
        print("\n✅ Сервер создан:")
        print(f"   Имя: {server_data['name']}")
        print(f"   Адрес: {server_data['ip']}:{server_data['port']}")
        print(f"   Защита паролем: {server_data['password_protected']}")
        if server_data['password_protected']:
            print(f"   Пароль: {'*' * len(server_data['password'])}")
        print(f"   Описание: {server_data['description']}")
    
    dialog.server_created.connect(on_server_created)
    
    if dialog.exec_() == QDialog.Accepted:
        print("Диалог закрыт с созданием сервера")
    else:
        print("Диалог закрыт без создания сервера")
    
    sys.exit(0)