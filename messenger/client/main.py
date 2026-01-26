"""
Точка входа клиентской части Local Messenger.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

# Импорт модулей из новой структуры
try:
    from ui.login_dialog import LoginDialog
    from ui.main_window import MainWindow
    from utils.auth_manager import get_auth_manager
    from utils.server_manager import get_server_manager
    from config import update_server_config, APP_NAME, APP_VERSION
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Проверьте структуру проекта и наличие необходимых модулей.")
    sys.exit(1)


class MessengerClient:
    """
    Основной класс клиента мессенджера.
    Управляет жизненным циклом приложения.
    """
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.auth_token = None
        self.current_user = None
        self.server_url = None
        self.server_data = None
        
        # Инициализация менеджеров
        self.auth_manager = get_auth_manager()
        self.server_manager = get_server_manager()
        
        # Настройка приложения
        self.app.setApplicationName(APP_NAME)
        self.app.setApplicationVersion(APP_VERSION)
        self.app.setOrganizationName("Local Messenger Team")
        
    def run(self):
        """Запуск клиента"""
        print("=" * 50)
        print(f"🚀 {APP_NAME} Client v{APP_VERSION}")
        print("=" * 50)
        
        try:
            # Автозапуск серверов
            self.auto_start_servers()
            
            # Показываем диалог авторизации
            login_dialog = LoginDialog()
            
            # Обработчик выбора сервера
            def on_server_selected(server_data):
                self.server_data = server_data
                self.auth_token = server_data.get('auth_token')
                self.current_user = server_data.get('user_data')
                
                # Обновляем конфигурацию сервера
                update_server_config(server_data['ip'], server_data['port'])
                self.server_url = f"http://{server_data['ip']}:{server_data['port']}"
                
                print(f"✅ Подключено к серверу: {server_data['name']}")
                print(f"   📡 Адрес: {server_data['ip']}:{server_data['port']}")
                print(f"   👤 Пользователь: {self.current_user.get('username')}")
                print(f"   🔒 Защита паролем: {'Да' if server_data.get('is_password_protected') else 'Нет'}")
                
            login_dialog.server_selected.connect(on_server_selected)
            
            if login_dialog.exec_():
                if self.auth_token and self.current_user and self.server_url:
                    # Показываем главное окно
                    main_window = MainWindow(self.auth_token, self.current_user, self.server_url)
                    main_window.show()
                    
                    # Сохраняем настройки
                    self.save_settings()
                    
                    return self.app.exec_()
                else:
                    QMessageBox.critical(None, "❌ Ошибка", 
                                       "Не удалось получить данные для подключения")
                    return 1
            else:
                print("🚪 Выход из приложения")
                return 0
                
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "❌ Критическая ошибка", 
                               f"Не удалось запустить приложение:\n{str(e)}")
            return 1
    
    def auto_start_servers(self):
        """Автозапуск серверов с флагом auto_start"""
        print("🔍 Проверка серверов для автозапуска...")
        
        try:
            servers = self.server_manager.get_server_list()
            auto_start_servers = [s for s in servers if s.get('auto_start', False)]
            
            if auto_start_servers:
                print(f"   Найдено серверов для автозапуска: {len(auto_start_servers)}")
                
                for server in auto_start_servers:
                    server_name = server['name']
                    
                    # Проверяем, запущен ли уже сервер
                    if not self.server_manager.check_server_connection(server_name):
                        print(f"   🚀 Запуск сервера: {server_name}")
                        
                        # Для автозапуска пропускаем серверы с паролями
                        if server.get('password_protected'):
                            print(f"   ⚠️ Сервер {server_name} требует пароль - пропускаем")
                            continue
                        
                        success, message = self.server_manager.start_server(server_name)
                        if success:
                            print(f"   ✅ {message}")
                        else:
                            print(f"   ❌ Ошибка: {message}")
                    else:
                        print(f"   ✅ Сервер {server_name} уже запущен")
            else:
                print("   ℹ️ Серверы для автозапуска не найдены")
                
        except Exception as e:
            print(f"   ⚠️ Ошибка при автозапуске серверов: {e}")
    
    def save_settings(self):
        """Сохранение настроек приложения"""
        try:
            # Сохраняем последние настройки
            if self.server_data:
                self.auth_manager.save_last_server(self.server_data)
            
            print("   💾 Настройки сохранены")
            
        except Exception as e:
            print(f"   ⚠️ Ошибка сохранения настроек: {e}")
    
    def cleanup(self):
        """Очистка ресурсов при завершении"""
        print("🧹 Очистка ресурсов...")
        # Здесь можно добавить закрытие всех соединений


def main():
    """Точка входа в приложение"""
    client = MessengerClient()
    
    try:
        exit_code = client.run()
        client.cleanup()
        return exit_code
    except KeyboardInterrupt:
        print("\n\n🚪 Приложение завершено пользователем")
        return 0
    except Exception as e:
        print(f"\n\n❌ Необработанное исключение: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())