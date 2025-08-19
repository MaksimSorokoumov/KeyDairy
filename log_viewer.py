
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import calendar
import datetime
from pathlib import Path
from typing import Optional
from encryption_utils import EncryptionManager

class LogViewer:
    """GUI для просмотра зашифрованных логов кейлогера"""

    def __init__(self, encryption_manager: EncryptionManager, log_dir: Path):
        self.encryption_manager = encryption_manager
        self.log_dir = log_dir
        self.selected_date = datetime.date.today()
        self.current_month = datetime.date.today().replace(day=1)

        self.root = tk.Tk()
        self.root.title("KeyDairy - Просмотр журналов")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Стиль
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.setup_ui()
        self.load_log_for_date(self.selected_date)

    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Заголовок
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(
            header_frame, 
            text="🔐 KeyDairy - Просмотр журналов клавиатуры",
            font=('Arial', 16, 'bold')
        )
        title_label.pack()

        # Основная область (календарь + логи)
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Левая панель - календарь и навигация
        left_panel = ttk.LabelFrame(content_frame, text="Навигация по дням", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.setup_calendar_panel(left_panel)
        self.setup_navigation_panel(left_panel)

        # Правая панель - содержимое логов
        right_panel = ttk.LabelFrame(content_frame, text="Содержимое журнала", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.setup_log_panel(right_panel)

        # Статус-бар
        self.setup_status_bar(main_container)

    def setup_calendar_panel(self, parent):
        """Настраивает панель календаря"""
        # Заголовок месяца с навигацией
        month_nav_frame = ttk.Frame(parent)
        month_nav_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(month_nav_frame, text="←", width=3,
                  command=self.prev_month).pack(side=tk.LEFT)

        self.month_label = ttk.Label(month_nav_frame, font=('Arial', 12, 'bold'))
        self.month_label.pack(side=tk.LEFT, expand=True)

        ttk.Button(month_nav_frame, text="→", width=3,
                  command=self.next_month).pack(side=tk.RIGHT)

        # Календарь
        self.calendar_frame = ttk.Frame(parent)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True)

        self.update_calendar()

    def setup_navigation_panel(self, parent):
        """Настраивает панель навигации по дням"""
        nav_frame = ttk.LabelFrame(parent, text="Быстрая навигация")
        nav_frame.pack(fill=tk.X, pady=(10, 0))

        # Кнопки навигации
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="← Предыдущий день",
                  command=self.prev_day).pack(fill=tk.X, pady=2)

        ttk.Button(button_frame, text="Следующий день →",
                  command=self.next_day).pack(fill=tk.X, pady=2)

        ttk.Button(button_frame, text="📅 Сегодня",
                  command=self.go_to_today).pack(fill=tk.X, pady=2)

        # Информация о выбранной дате
        date_info_frame = ttk.Frame(nav_frame)
        date_info_frame.pack(fill=tk.X, padx=5, pady=(10, 5))

        ttk.Label(date_info_frame, text="Выбранная дата:").pack()
        self.selected_date_label = ttk.Label(date_info_frame, 
                                           font=('Arial', 10, 'bold'),
                                           foreground='blue')
        self.selected_date_label.pack()

    def setup_log_panel(self, parent):
        """Настраивает панель просмотра логов"""
        # Информация о файле
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_info_label = ttk.Label(info_frame, text="", font=('Arial', 9))
        self.file_info_label.pack(anchor=tk.W)

        # Текстовая область для логов
        self.log_text = scrolledtext.ScrolledText(
            parent, 
            wrap=tk.WORD,
            font=('Consolas', 10),
            state=tk.DISABLED,
            bg='#f8f9fa',
            fg='#212529'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Кнопки управления
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame, text="🔄 Обновить",
                  command=self.refresh_current_log).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(buttons_frame, text="📋 Копировать всё",
                  command=self.copy_all_text).pack(side=tk.LEFT, padx=5)

        ttk.Button(buttons_frame, text="🗑️ Очистить отображение",
                  command=self.clear_display).pack(side=tk.LEFT, padx=5)

        # Кнопка для автоматической конвертации раскладки (EN -> RU) по метке layout в заголовках
        ttk.Button(buttons_frame, text="🔁 Конверт раскладки",
                  command=self.auto_convert_layout).pack(side=tk.LEFT, padx=5)

    def setup_status_bar(self, parent):
        """Настраивает статус-бар"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # Создаем сепаратор
        separator = ttk.Separator(self.status_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(0, 5))

        self.status_label = ttk.Label(self.status_frame, text="Готов к работе")
        self.status_label.pack(side=tk.LEFT)

        # Индикатор количества записей
        self.records_label = ttk.Label(self.status_frame, text="")
        self.records_label.pack(side=tk.RIGHT)

    def update_calendar(self):
        """Обновляет отображение календаря"""
        # Очищаем предыдущий календарь
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        # Обновляем заголовок месяца
        month_name = calendar.month_name[self.current_month.month]
        year = self.current_month.year
        self.month_label.config(text=f"{month_name} {year}")

        # Дни недели
        days_frame = ttk.Frame(self.calendar_frame)
        # Размещаем заголовки дней недели в первой строке сетки календаря
        days_frame.grid(row=0, column=0, columnspan=7, sticky='ew', pady=(0, 5))

        for i, day_name in enumerate(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']):
            label = ttk.Label(days_frame, text=day_name, 
                             font=('Arial', 8, 'bold'), width=4)
            label.grid(row=0, column=i, padx=1, pady=1)

        # Дни месяца
        cal = calendar.monthcalendar(self.current_month.year, self.current_month.month)

        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    # Пустая ячейка
                    widget = ttk.Label(self.calendar_frame, text="", width=4)
                else:
                    # Создаем дату для этого дня
                    day_date = datetime.date(self.current_month.year, self.current_month.month, day)

                    # Проверяем, есть ли лог для этого дня
                    has_log = self.has_log_for_date(day_date)

                    widget = ttk.Button(
                        self.calendar_frame,
                        text=str(day),
                        width=4,
                        command=lambda d=day_date: self.select_date(d)
                    )

                    # Применяем стили
                    if day_date == self.selected_date:
                        widget.configure(style='Selected.TButton')
                    elif day_date == datetime.date.today():
                        widget.configure(style='Today.TButton')
                    elif has_log:
                        # подсветка дней с логами, если стиль применим
                        try:
                            widget.configure(style='HasLog.TButton')
                        except:
                            pass

                widget.grid(row=week_num + 1, column=day_num, padx=1, pady=1)

        self.configure_calendar_styles()

    def configure_calendar_styles(self):
        """Настраивает стили для календаря"""
        try:
            self.style.configure('Selected.TButton', background='#0066cc', foreground='white')
            self.style.configure('Today.TButton', background='#28a745', foreground='white')
            self.style.configure('HasLog.TButton', background='#ffc107', foreground='black')
        except:
            pass  # Игнорируем ошибки стилей

    def select_date(self, date):
        """Выбирает дату и загружает соответствующий лог"""
        self.selected_date = date
        self.update_calendar()
        self.load_log_for_date(date)
        self.update_selected_date_display()

    def load_log_for_date(self, date):
        """Загружает лог для указанной даты"""
        log_file = self.get_log_file_path(date)

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)

        if log_file and log_file.exists():
            try:
                decrypted_content = self.encryption_manager.decrypt_file(log_file)
                self.log_text.insert(1.0, decrypted_content)

                # Подсчитываем записи
                lines = decrypted_content.split('\n')
                record_count = len([line for line in lines if line.strip().startswith('[')])

                self.file_info_label.config(
                    text=f"Файл: {log_file.name} | Размер: {log_file.stat().st_size} байт"
                )
                self.records_label.config(text=f"Записей: {record_count}")
                self.status_label.config(text=f"Загружен журнал за {date.strftime('%d.%m.%Y')}")

            except Exception as e:
                error_msg = f"Ошибка при загрузке файла: {e}"
                self.log_text.insert(1.0, error_msg)
                self.status_label.config(text="Ошибка загрузки")
                self.records_label.config(text="")
        else:
            no_data_msg = f"Нет данных за {date.strftime('%d.%m.%Y')}\n\n"
            no_data_msg += "Возможные причины:\n"
            no_data_msg += "• Кейлогер не был запущен в этот день\n"
            no_data_msg += "• Не было активности на клавиатуре\n"
            no_data_msg += "• Файл журнала был удален"

            self.log_text.insert(1.0, no_data_msg)
            self.file_info_label.config(text="Файл отсутствует")
            self.records_label.config(text="Записей: 0")
            self.status_label.config(text=f"Нет данных за {date.strftime('%d.%m.%Y')}")

        self.log_text.config(state=tk.DISABLED)

    def get_log_file_path(self, date) -> Optional[Path]:
        """Получает путь к файлу лога для указанной даты"""
        year_month_dir = self.log_dir / str(date.year) / calendar.month_name[date.month]
        log_file = year_month_dir / f"{date.day}.enc"
        return log_file if year_month_dir.exists() else None

    def has_log_for_date(self, date) -> bool:
        """Проверяет, существует ли лог для указанной даты"""
        log_file = self.get_log_file_path(date)
        return log_file and log_file.exists()

    def prev_day(self):
        """Переходит к предыдущему дню"""
        self.selected_date -= datetime.timedelta(days=1)

        # Обновляем месяц если нужно
        if self.selected_date.month != self.current_month.month or \
           self.selected_date.year != self.current_month.year:
            self.current_month = self.selected_date.replace(day=1)
            self.update_calendar()
        else:
            self.update_calendar()

        self.load_log_for_date(self.selected_date)
        self.update_selected_date_display()

    def next_day(self):
        """Переходит к следующему дню"""
        self.selected_date += datetime.timedelta(days=1)

        # Обновляем месяц если нужно
        if self.selected_date.month != self.current_month.month or \
           self.selected_date.year != self.current_month.year:
            self.current_month = self.selected_date.replace(day=1)
            self.update_calendar()
        else:
            self.update_calendar()

        self.load_log_for_date(self.selected_date)
        self.update_selected_date_display()

    def go_to_today(self):
        """Переходит к сегодняшней дате"""
        today = datetime.date.today()
        self.select_date(today)
        self.current_month = today.replace(day=1)
        self.update_calendar()

    def prev_month(self):
        """Переходит к предыдущему месяцу"""
        if self.current_month.month == 1:
            self.current_month = self.current_month.replace(year=self.current_month.year-1, month=12)
        else:
            self.current_month = self.current_month.replace(month=self.current_month.month-1)
        self.update_calendar()

    def next_month(self):
        """Переходит к следующему месяцу"""
        if self.current_month.month == 12:
            self.current_month = self.current_month.replace(year=self.current_month.year+1, month=1)
        else:
            self.current_month = self.current_month.replace(month=self.current_month.month+1)
        self.update_calendar()

    def update_selected_date_display(self):
        """Обновляет отображение выбранной даты"""
        formatted_date = self.selected_date.strftime('%d.%m.%Y (%A)')
        # Переводим название дня недели
        day_names = {
            'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
            'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье'
        }
        for eng, rus in day_names.items():
            formatted_date = formatted_date.replace(eng, rus)

        self.selected_date_label.config(text=formatted_date)

    def refresh_current_log(self):
        """Обновляет текущий лог"""
        self.load_log_for_date(self.selected_date)

    def copy_all_text(self):
        """Копирует весь текст в буфер обмена"""
        try:
            content = self.log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_label.config(text="Текст скопирован в буфер обмена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать текст: {e}")

    def translit_en_to_ru(self, text: str) -> str:
        """Конвертирует текст, набранный в английской раскладке, в русские буквы по раскладке клавиатуры."""
        mapping = {
            'q':'й','w':'ц','e':'у','r':'к','t':'е','y':'н','u':'г','i':'ш','o':'щ','p':'з','[':'х',']':'ъ',
            'a':'ф','s':'ы','d':'в','f':'а','g':'п','h':'р','j':'о','k':'л','l':'д',';':'ж',"'":'э',
            'z':'я','x':'ч','c':'с','v':'м','b':'и','n':'т','m':'ь',',':'б','.':'ю','/':'.'
        }
        result_chars = []
        for ch in text:
            lower = ch.lower()
            if lower in mapping:
                mapped = mapping[lower]
                # сохраняем регистр
                if ch.isupper():
                    mapped = mapped.upper()
                result_chars.append(mapped)
            else:
                result_chars.append(ch)
        return ''.join(result_chars)

    def auto_convert_layout(self):
        """Ищет заголовки с меткой layout:en и конвертирует последующие блоки из латиницы в кириллицу."""
        try:
            self.log_text.config(state=tk.NORMAL)
            full = self.log_text.get(1.0, tk.END)

            lines = full.splitlines(keepends=True)
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.lstrip().startswith('## [') and 'layout:en' in line:
                    # конвертируем последующие строки до следующего заголовка '## [' или конца
                    j = i + 1
                    while j < len(lines) and not lines[j].lstrip().startswith('## ['):
                        lines[j] = self.translit_en_to_ru(lines[j])
                        j += 1
                    i = j
                else:
                    i += 1

            new_text = ''.join(lines)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(1.0, new_text)
            self.log_text.config(state=tk.DISABLED)
            self.status_label.config(text="Конвертация раскладки выполнена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось конвертировать раскладку: {e}")

    def clear_display(self):
        """Очищает отображение текста"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.status_label.config(text="Отображение очищено")

    def run(self):
        """Запускает GUI"""
        self.update_selected_date_display()
        self.root.mainloop()

# Функция для тестирования GUI отдельно
def main():
    """Основная функция для тестирования"""
    import tempfile

    # Создаем временные директории для тестирования
    temp_dir = Path(tempfile.mkdtemp())
    log_dir = temp_dir / "logs"
    config_file = temp_dir / "config.json"

    # Создаем тестовый пароль
    test_password = "test123"
    encryption_manager = EncryptionManager(test_password)
    encryption_manager.save_config(config_file)

    # Создаем тестовые логи
    create_test_logs(encryption_manager, log_dir)

    # Запускаем GUI
    viewer = LogViewer(encryption_manager, log_dir)
    viewer.run()

    # Очистка
    import shutil
    shutil.rmtree(temp_dir)

def create_test_logs(encryption_manager, log_dir):
    """Создает тестовые логи для демонстрации"""
    test_dates = [
        (datetime.date(2024, 8, 15), "# Журнал клавиатуры за 2024-08-15\n\n## [09:15:23] Chrome - google.com\n\npython keylogger tutorial\n\n## [10:30:25] VSCode - main.py\n\ndef encrypt_data(text, password):\n    pass\n\n"),
        (datetime.date(2024, 8, 16), "# Журнал клавиатуры за 2024-08-16\n\n## [08:30:15] Chrome - youtube.com\n\nwatching Python tutorials\n\n## [14:30:12] Notepad - shopping.txt\n\nmilk, bread, eggs, cheese\n\n"),
        (datetime.date.today(), f"# Журнал клавиатуры за {datetime.date.today()}\n\n## [09:00:12] Текущая активность\n\nПросмотр журналов KeyDairy\n\n")
    ]

    for test_date, content in test_dates:
        year_month_dir = log_dir / str(test_date.year) / calendar.month_name[test_date.month]
        year_month_dir.mkdir(parents=True, exist_ok=True)

        log_file = year_month_dir / f"{test_date.day}.enc"
        encryption_manager.encrypt_to_file(content, log_file)

if __name__ == "__main__":
    main()
