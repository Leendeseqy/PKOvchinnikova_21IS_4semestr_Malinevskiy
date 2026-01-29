"""
Test suite for Educational Planner application.
Тестирует только бизнес-логику, без создания GUI элементов.
Run with: pytest test_planner.py -v
"""

import pytest
import sqlite3
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Мокаем tkinter до импорта основного класса
import sys
sys.modules['tkinter'] = Mock()
sys.modules['tkinter.ttk'] = Mock()
sys.modules['tkinter.messagebox'] = Mock()

# Теперь импортируем основной класс
from planner import EducationalPlanner


@pytest.fixture
def mock_tkinter():
    """Фикстура для мока tkinter."""
    # Мокаем tkinter модули
    tk_mock = Mock()
    ttk_mock = Mock()
    messagebox_mock = Mock()

    # Настраиваем моки
    tk_mock.Tk = Mock()
    tk_mock.Tk.return_value = Mock()
    tk_mock.StringVar = Mock()
    tk_mock.BooleanVar = Mock()
    tk_mock.Text = Mock()
    tk_mock.Spinbox = Mock()
    tk_mock.END = 'end'

    ttk_mock.Notebook = Mock()
    ttk_mock.Frame = Mock()
    ttk_mock.LabelFrame = Mock()
    ttk_mock.Button = Mock()
    ttk_mock.Label = Mock()
    ttk_mock.Entry = Mock()
    ttk_mock.Combobox = Mock()
    ttk_mock.Checkbutton = Mock()
    ttk_mock.Treeview = Mock()
    ttk_mock.Scrollbar = Mock()

    messagebox_mock.showwarning = Mock()
    messagebox_mock.showinfo = Mock()
    messagebox_mock.showerror = Mock()
    messagebox_mock.askyesno = Mock()

    # Патчим модули
    with patch.dict('sys.modules', {
        'tkinter': tk_mock,
        'tkinter.ttk': ttk_mock,
        'tkinter.messagebox': messagebox_mock
    }):
        yield tk_mock, ttk_mock, messagebox_mock


@pytest.fixture
def temp_db():
    """Фикстура для создания временной базы данных."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    # Создаем соединение с временной БД
    conn = sqlite3.connect(db_path)
    yield conn, db_path

    # Очистка после тестов
    conn.close()
    os.unlink(db_path)


@pytest.fixture
def planner_app(mock_tkinter):
    """Фикстура для создания экземпляра приложения с моками."""
    tk_mock, ttk_mock, messagebox_mock = mock_tkinter

    # Мокаем корневое окно
    root_mock = Mock()
    root_mock.title = Mock()
    root_mock.geometry = Mock()
    root_mock.wait_window = Mock()

    # Мокаем Notebook и другие виджеты
    notebook_mock = Mock()
    ttk_mock.Notebook.return_value = notebook_mock

    # Создаем приложение с временной БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    # Мокаем подключение к БД
    with patch('planner.sqlite3.connect') as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Настраиваем мок курсора для возврата данных
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = None
        mock_cursor.lastrowid = 1

        # Создаем приложение
        app = EducationalPlanner(root_mock)

        # Сохраняем моки для использования в тестах
        app.mock_root = root_mock
        app.mock_conn = mock_conn
        app.mock_cursor = mock_cursor
        app.mock_messagebox = messagebox_mock

        # Сохраняем путь к временной БД для очистки
        app.temp_db_path = db_path

        yield app

    # Очистка
    os.unlink(db_path)


@pytest.fixture
def planner_app_real_db(mock_tkinter):
    """Фикстура для создания приложения с реальной БД (без моков)."""
    tk_mock, ttk_mock, messagebox_mock = mock_tkinter

    # Мокаем корневое окно
    root_mock = Mock()

    # Создаем временную БД
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    # Патчим подключение к БД для использования временного файла
    with patch('planner.sqlite3.connect') as mock_connect:
        # Используем реальное соединение с временной БД
        real_conn = sqlite3.connect(db_path)
        mock_connect.return_value = real_conn

        # Создаем приложение
        app = EducationalPlanner(root_mock)

        # Сохраняем соединение
        app.real_conn = real_conn
        app.temp_db_path = db_path

        yield app

    # Очистка
    real_conn.close()
    os.unlink(db_path)


@pytest.fixture
def sample_competencies_file():
    """Фикстура для создания временного файла компетенций."""
    competencies = [
        {
            "название": "Программирование на Python",
            "категория": "Технические"
        },
        {
            "название": "Анализ данных",
            "категория": "Аналитические"
        }
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(competencies, f, ensure_ascii=False, indent=4)
        file_path = f.name

    yield file_path
    os.unlink(file_path)


class TestDatabaseOperations:
    """Тесты для операций с базой данных."""

    def test_detect_db_type_sqlite(self, mock_tkinter):
        """Тест определения типа БД как SQLite."""
        with patch('planner.POSTGRES_AVAILABLE', False):
            root_mock = Mock()
            app = EducationalPlanner(root_mock)
            assert app.db_type == 'sqlite'

    def test_detect_db_type_postgres(self, mock_tkinter):
        """Тест определения типа БД как PostgreSQL."""
        with patch('planner.POSTGRES_AVAILABLE', True):
            with patch('planner.psycopg2.connect') as mock_connect:
                mock_conn = Mock()
                mock_conn.close = Mock()
                mock_connect.return_value = mock_conn

                root_mock = Mock()
                app = EducationalPlanner(root_mock)
                assert app.db_type == 'postgres'

    def test_detect_db_type_postgres_fallback(self, mock_tkinter):
        """Тест fallback на SQLite при недоступности PostgreSQL."""
        with patch('planner.POSTGRES_AVAILABLE', True):
            with patch('planner.psycopg2.connect', side_effect=Exception('Connection failed')):
                root_mock = Mock()
                app = EducationalPlanner(root_mock)
                assert app.db_type == 'sqlite'

    def test_check_and_create_competencies_json_exists(self, planner_app):
        """Тест проверки существующего файла компетенций."""
        app = planner_app

        with patch('planner.os.path.exists', return_value=True):
            with patch('planner.json.dump') as mock_dump:
                app.check_and_create_competencies_json()
                mock_dump.assert_not_called()

    def test_check_and_create_competencies_json_not_exists(self, planner_app):
        """Тест создания файла компетенций при его отсутствии."""
        app = planner_app

        with patch('planner.os.path.exists', return_value=False):
            with patch('planner.json.dump') as mock_dump:
                app.check_and_create_competencies_json()
                mock_dump.assert_called_once()


class TestBusinessLogic:
    """Тесты бизнес-логики."""

    def test_validate_date_correct(self, planner_app):
        """Тест валидации корректной даты."""
        app = planner_app
        assert app.validate_date("2023-12-31") is True
        assert app.validate_date("2023-01-01") is True
        assert app.validate_date("") is True  # Пустая строка допустима

    def test_validate_date_incorrect(self, planner_app):
        """Тест валидации некорректной даты."""
        app = planner_app
        assert app.validate_date("2023-13-01") is False
        assert app.validate_date("2023-01-32") is False
        assert app.validate_date("not-a-date") is False

    @pytest.mark.parametrize("date_str,expected", [
        ("2023-12-31", True),
        ("2023-01-01", True),
        ("2023-13-01", False),
        ("2023-01-32", False),
        ("", True),
        ("not-a-date", False),
        ("2023-02-29", False),  # 2023 не високосный
        ("2024-02-29", True),   # 2024 високосный
    ])
    def test_validate_date_parametrized(self, planner_app, date_str, expected):
        """Параметризованный тест валидации дат."""
        app = planner_app
        assert app.validate_date(date_str) == expected

    def test_load_competencies_from_json(self, planner_app, sample_competencies_file):
        """Тест загрузки компетенций из JSON файла."""
        app = planner_app

        # Мокаем проверку пустой таблицы
        app.mock_cursor.fetchone.return_value = (0,)

        with patch('planner.os.path.exists', return_value=True):
            with patch('planner.json.load') as mock_json_load:
                competencies = [
                    {"название": "Test Comp", "категория": "Test Category"}
                ]
                mock_json_load.return_value = competencies

                app.load_competencies_from_json()

                # Проверяем, что был вызван INSERT
                app.mock_cursor.execute.assert_any_call(
                    "INSERT INTO компетенции (название, категория) VALUES (?, ?)",
                    ("Test Comp", "Test Category")
                )
                app.mock_conn.commit.assert_called_once()

    def test_load_skills_autocomplete(self, planner_app):
        """Тест загрузки навыков для автодополнения."""
        app = planner_app

        # Мокаем результат выборки
        app.mock_cursor.fetchall.return_value = [("Python",), ("SQL",), ("Git",)]

        app.load_skills_autocomplete()

        # Проверяем выполнение запроса
        app.mock_cursor.execute.assert_called_with("SELECT название FROM навыки")
        assert app.skills_autocomplete == ["Python", "SQL", "Git"]

    def test_grant_achievement(self, planner_app):
        """Тест выдачи достижения."""
        app = planner_app

        app.grant_achievement('test_achievement')

        # Проверяем выполнение UPDATE запроса
        app.mock_cursor.execute.assert_called_with(
            'UPDATE достижения SET получено = 1 WHERE код = ? AND получено = 0',
            ('test_achievement',)
        )
        app.mock_conn.commit.assert_called_once()


class TestGoalsOperations:
    """Тесты для операций с целями."""

    def test_add_goal(self, planner_app):
        """Тест добавления новой цели."""
        app = planner_app

        # Мокаем treeview
        app.goals_tree = Mock()

        # Мокаем диалоговое окно
        with patch('planner.GoalDialog') as mock_dialog:
            mock_dialog_instance = Mock()
            mock_dialog.return_value = mock_dialog_instance
            mock_dialog_instance.dialog = Mock()

            app.add_goal()

            # Проверяем, что диалог был создан
            mock_dialog.assert_called_once()

    def test_delete_goal_no_selection(self, planner_app):
        """Тест удаления цели без выбора."""
        app = planner_app

        # Мокаем treeview
        app.goals_tree = Mock()
        app.goals_tree.selection.return_value = []

        app.delete_goal()

        # Проверяем показ предупреждения
        app.mock_messagebox.showwarning.assert_called_with(
            "Предупреждение", "Выберите цель для удаления"
        )

    def test_delete_goal_with_selection(self, planner_app):
        """Тест удаления выбранной цели."""
        app = planner_app

        # Настраиваем моки
        app.goals_tree = Mock()
        app.goals_tree.selection.return_value = ['item1']
        app.goals_tree.item.return_value = {'values': [1, 'Test Goal']}

        # Мокаем messagebox
        app.mock_messagebox.askyesno.return_value = True

        app.delete_goal()

        # Проверяем удаление
        assert app.mock_cursor.execute.call_count >= 3
        app.mock_conn.commit.assert_called_once()
        app.mock_messagebox.showinfo.assert_called_with("Успех", "Цель удалена")

    def test_check_achievements_start(self, planner_app):
        """Тест проверки достижения 'Старт'."""
        app = planner_app

        # Настраиваем моки
        app.mock_cursor.fetchone.return_value = (1,)  # COUNT(*) FROM цели > 0

        app.check_achievements()

        # Проверяем, что достижение было выдано
        app.mock_cursor.execute.assert_any_call(
            'UPDATE достижения SET получено = 1 WHERE код = ? AND получено = 0',
            ('start',)
        )

    def test_check_achievements_punctual(self, planner_app):
        """Тест проверки достижения 'Пунктуальный'."""
        app = planner_app

        # Настраиваем моки
        app.mock_cursor.fetchone.side_effect = [
            (5,),  # COUNT(*) FROM цели > 0
            (3,),  # Три цели завершены в срок
        ]

        app.check_achievements()

        # Проверяем выдачу достижения
        app.mock_cursor.execute.assert_any_call(
            'UPDATE достижения SET получено = 1 WHERE код = ? AND получено = 0',
            ('punctual',)
        )


class TestSemesterGoals:
    """Тесты для целей на семестр."""

    def test_load_semester_goals(self, planner_app):
        """Тест загрузки целей на семестр."""
        app = planner_app

        # Мокаем treeview
        app.semester_tree = Mock()

        # Мокаем результат выборки
        app.mock_cursor.fetchall.return_value = [
            (1, 'Изучить Python', 'Количество', 2, 5)
        ]

        app.load_semester_goals()

        # Проверяем выполнение запроса
        app.mock_cursor.execute.assert_called_with(
            '''SELECT id, текст_цели, тип_цели, текущий_прогресс, целевой_прогресс
               FROM цель_на_семестр'''
        )

    def test_update_semester_progress_no_selection(self, planner_app):
        """Тест обновления прогресса без выбора цели."""
        app = planner_app

        # Мокаем treeview
        app.semester_tree = Mock()
        app.semester_tree.selection.return_value = []

        app.update_semester_progress()

        # Проверяем показ предупреждения
        app.mock_messagebox.showwarning.assert_called_with(
            "Предупреждение", "Выберите цель"
        )

    def test_update_semester_progress_count_type(self, planner_app):
        """Тест обновления прогресса для цели типа 'Количество'."""
        app = planner_app

        # Настраиваем моки
        app.semester_tree = Mock()
        app.semester_tree.selection.return_value = ['item1']
        app.semester_tree.item.return_value = {
            'values': [1, 'Test Goal', 'Количество', '2 из 5', 5]
        }

        # Мокаем результаты запросов
        app.mock_cursor.fetchone.return_value = (3,)  # COUNT(*) FROM цели WHERE статус = 'Завершено'

        app.update_semester_progress()

        # Проверяем обновление прогресса
        app.mock_cursor.execute.assert_any_call(
            'UPDATE цель_на_семестр SET текущий_прогресс = ? WHERE id = ?',
            (3, 1)
        )
        app.mock_conn.commit.assert_called_once()


class TestProfileAndCompetencies:
    """Тесты для профиля и компетенций."""

    def test_update_profile(self, planner_app):
        """Тест обновления статистики профиля."""
        app = planner_app

        # Мокаем текстовые поля
        app.skills_text = Mock()
        app.types_text = Mock()
        app.timely_label = Mock()

        # Мокаем результаты запросов
        app.mock_cursor.fetchall.side_effect = [
            [("Python", 5), ("SQL", 3)],  # Навыки
            [("Курс", 3, 5), ("Проект", 2, 3)],  # Типы целей
        ]

        # Для своевременности
        app.mock_cursor.fetchone.return_value = (4, 5)  # 4 из 5 вовремя

        app.update_profile()

        # Проверяем выполнение запросов
        assert app.mock_cursor.execute.call_count >= 2

        # Проверяем обновление текстовых полей
        app.skills_text.insert.assert_called()
        app.types_text.insert.assert_called()
        app.timely_label.config.assert_called()

    def test_update_profile_no_completed_goals(self, planner_app):
        """Тест обновления профиля без завершенных целей."""
        app = planner_app

        # Мокаем поля
        app.skills_text = Mock()
        app.types_text = Mock()
        app.timely_label = Mock()

        # Мокаем результат для своевременности
        app.mock_cursor.fetchall.side_effect = [
            [],  # Нет навыков
            [],  # Нет типов целей
        ]

        app.mock_cursor.fetchone.return_value = (0, 0)  # Нет завершенных целей

        app.update_profile()

        # Проверяем обработку случая без данных
        app.timely_label.config.assert_called()

    def test_update_competencies(self, planner_app):
        """Тест обновления информации о компетенциях."""
        app = planner_app

        # Мокаем текстовые поля
        app.avg_text = Mock()
        app.weak_text = Mock()
        app.rec_text = Mock()

        # Мокаем результаты запросов
        app.mock_cursor.fetchall.return_value = [
            ("Python", "Технические", 4.5, 3),
            ("Коммуникации", "Социальные", 2.0, 1),
        ]

        app.update_competencies()

        # Проверяем выполнение запроса
        app.mock_cursor.execute.assert_called()

        # Проверяем обновление текстовых полей
        assert app.avg_text.insert.call_count > 0
        assert app.weak_text.insert.call_count > 0
        assert app.rec_text.insert.call_count > 0

    def test_update_achievements(self, planner_app):
        """Тест обновления списка достижений."""
        app = planner_app

        # Мокаем текстовое поле
        app.achievements_text = Mock()

        # Мокаем результаты запроса
        app.mock_cursor.fetchall.return_value = [
            ("Старт", "Первая цель", 1),
            ("Пунктуальный", "Три цели в срок", 0),
        ]

        app.update_achievements()

        # Проверяем выполнение запроса
        app.mock_cursor.execute.assert_called_with(
            'SELECT название, описание, получено FROM достижения ORDER BY получено DESC, код'
        )

        # Проверяем вставку в текстовое поле
        app.achievements_text.insert.assert_called()


class TestSettings:
    """Тесты для настроек."""

    def test_save_specialty(self, planner_app):
        """Тест сохранения специальности."""
        app = planner_app

        # Устанавливаем специальность
        app.specialty_var = Mock()
        app.specialty_var.get.return_value = "Информационные системы"

        app.save_specialty()

        # Проверяем сохранение
        assert app.specialty == "Информационные системы"
        app.mock_messagebox.showinfo.assert_called_with(
            "Успех", "Специальность сохранена: Информационные системы"
        )

    def test_save_specialty_empty(self, planner_app):
        """Тест сохранения пустой специальности."""
        app = planner_app

        app.specialty_var = Mock()
        app.specialty_var.get.return_value = ""

        app.save_specialty()

        # Проверяем, что сообщение не показывается
        app.mock_messagebox.showinfo.assert_not_called()


class TestEdgeCases:
    """Тесты для крайних случаев."""

    def test_conn_rollback_on_error(self, planner_app):
        """Тест отката транзакции при ошибке."""
        app = planner_app

        # Симулируем ошибку при выполнении запроса
        app.mock_cursor.execute.side_effect = sqlite3.Error("Test error")

        try:
            # Вызываем метод, который должен обработать ошибку
            app.load_goals()
        except:
            pass

        # Проверяем, что был выполнен rollback
        app.mock_conn.rollback.assert_called_once()

    def test_preview_markdown(self, planner_app):
        """Тест предпросмотра Markdown."""
        app = planner_app

        # Мокаем виджет
        mock_widget = Mock()

        # Тестовый текст
        test_text = "# Заголовок\n- Пункт списка\n**жирный**"

        app.preview_markdown(test_text, mock_widget)

        # Проверяем вставку текста
        assert mock_widget.insert.call_count > 0


class TestReportGeneration:
    """Тесты для генерации отчетов."""

    @patch('planner.Document')
    @patch('planner.os.startfile')
    def test_generate_report_success(self, mock_startfile, mock_document, planner_app):
        """Тест успешной генерации отчета."""
        app = planner_app

        # Мокаем результаты запросов
        app.mock_cursor.fetchall.side_effect = [
            [],  # Цели
            [],  # Навыки
            [],  # Компетенции
            [],  # Достижения
            [],  # Цели на семестр
        ]

        # Мокаем дату
        with patch('planner.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '2023-12-31'

            app.generate_report()

            # Проверяем создание документа
            mock_document.assert_called_once()

    @patch('planner.Document')
    def test_generate_report_error(self, mock_document, planner_app):
        """Тест генерации отчета с ошибкой."""
        app = planner_app

        # Мокаем исключение
        app.mock_cursor.execute.side_effect = Exception("Database error")

        app.generate_report()

        # Проверяем сообщение об ошибке
        app.mock_messagebox.showerror.assert_called_once()

    def test_add_markdown_to_doc(self, planner_app):
        """Тест обработки Markdown текста."""
        app = planner_app

        # Мокаем документ и параграф
        mock_doc = Mock()
        mock_paragraph = Mock()
        mock_doc.add_paragraph.return_value = mock_paragraph
        mock_paragraph.add_run = Mock(return_value=Mock())

        # Тестовый текст с Markdown
        test_text = "# Заголовок\n* Список\n**жирный текст**"

        with patch.object(app, 'process_inline_formatting'):
            app.add_markdown_to_doc(mock_doc, test_text)

            # Проверяем добавление заголовка
            mock_doc.add_heading.assert_called_once()

    def test_process_inline_formatting(self, planner_app):
        """Тест обработки встроенного форматирования."""
        app = planner_app

        # Мокаем параграф
        mock_paragraph = Mock()
        mock_run = Mock()
        mock_paragraph.add_run.return_value = mock_run

        # Тест с обычным текстом
        app.process_inline_formatting(mock_paragraph, "Простой текст")
        mock_paragraph.add_run.assert_called_with("Простой текст")


class TestIntegration:
    """Интеграционные тесты с реальной БД."""

    def test_complete_goal_flow(self, temp_db):
        """Тест полного цикла работы с целью."""
        conn, db_path = temp_db

        # Инициализируем БД
        cursor = conn.cursor()

        # Создаем таблицы (упрощенная версия)
        cursor.execute('''
            CREATE TABLE цели (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                название TEXT NOT NULL,
                тип TEXT NOT NULL,
                статус TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE навыки (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                название TEXT UNIQUE NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE цель_навыки (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                цель_id INTEGER,
                навык_id INTEGER
            )
        ''')

        # Добавляем тестовые данные
        cursor.execute(
            "INSERT INTO цели (название, тип, статус) VALUES (?, ?, ?)",
            ("Тестовая цель", "Курс", "В процессе")
        )
        goal_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO навыки (название) VALUES (?)",
            ("Python",)
        )
        skill_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO цель_навыки (цель_id, навык_id) VALUES (?, ?)",
            (goal_id, skill_id)
        )

        conn.commit()

        # Проверяем данные
        cursor.execute("SELECT COUNT(*) FROM цели")
        assert cursor.fetchone()[0] == 1

        cursor.execute('''
            SELECT ц.название, н.название 
            FROM цели ц
            JOIN цель_навыки цн ON ц.id = цн.цель_id
            JOIN навыки н ON цн.навык_id = н.id
        ''')
        result = cursor.fetchone()
        assert result[0] == "Тестовая цель"
        assert result[1] == "Python"

        # Обновляем статус цели
        cursor.execute(
            "UPDATE цели SET статус = ? WHERE id = ?",
            ("Завершено", goal_id)
        )
        conn.commit()

        cursor.execute("SELECT статус FROM цели WHERE id = ?", (goal_id,))
        assert cursor.fetchone()[0] == "Завершено"

    def test_achievements_flow(self, temp_db):
        """Тест полного цикла работы с достижениями."""
        conn, db_path = temp_db

        # Создаем таблицу достижений
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE достижения (
                код TEXT PRIMARY KEY,
                название TEXT NOT NULL,
                описание TEXT,
                получено INTEGER DEFAULT 0
            )
        ''')

        # Добавляем тестовое достижение
        cursor.execute(
            "INSERT INTO достижения (код, название, описание, получено) VALUES (?, ?, ?, ?)",
            ("test", "Тестовое", "Тестовое достижение", 0)
        )

        # Выдаем достижение
        cursor.execute(
            "UPDATE достижения SET получено = 1 WHERE код = ? AND получено = 0",
            ("test",)
        )
        conn.commit()

        # Проверяем
        cursor.execute("SELECT получено FROM достижения WHERE код = ?", ("test",))
        assert cursor.fetchone()[0] == 1

    def test_real_db_operations(self, planner_app_real_db):
        """Тест операций с реальной БД."""
        app = planner_app_real_db

        # Тест инициализации БД
        cursor = app.real_conn.cursor()

        # Проверяем создание таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = [
            'цели', 'навыки', 'цель_навыки', 'компетенции',
            'цель_компетенции', 'достижения', 'цель_на_семестр'
        ]

        for table in expected_tables:
            assert table in tables

        # Проверяем заполнение таблицы достижений
        cursor.execute("SELECT COUNT(*) FROM достижения")
        assert cursor.fetchone()[0] == 5  # 5 предопределенных достижений


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])