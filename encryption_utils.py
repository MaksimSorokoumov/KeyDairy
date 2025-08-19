
import base64
import json
import os
from pathlib import Path
import win32crypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionManager:
    """Управление ключами и шифрованием.

    Схема:
    - Генерируем случайный ключ данных (DEK) один раз при первом запуске.
    - DEK храним в конфиге в двух видах:
        1) dek_by_password: DEK, зашифрованный ключом из пароля (KEK = PBKDF2(password, salt)).
        2) dek_by_dpapi: DEK, защищённый DPAPI для фоновой записи без пароля.
    - Для записи без пароля используем from_dpapi(); для просмотра логов — from_password().
    """

    def __init__(self, fernet_key: bytes):
        self.password = None
        self.salt = None
        self.iterations = 100000
        self.dek = fernet_key
        self.fernet = Fernet(fernet_key)

    @classmethod
    def from_dpapi(cls, config_path: Path):
        """Загружает DEK через DPAPI для фоновой записи без пароля."""
        with open(config_path, 'r') as f:
            config = json.load(f)

        if 'dek_by_dpapi' not in config:
            raise ValueError('В конфигурации отсутствует dek_by_dpapi')

        protected = base64.b64decode(config['dek_by_dpapi'])
        dek = win32crypt.CryptUnprotectData(protected, None, None, None, 0)[1]

        return cls(dek)

    @classmethod
    def from_password(cls, password: str, config_path: Path):
        """Загружает DEK, расшифровывая его ключом из пароля пользователя (KEK)."""
        with open(config_path, 'r') as f:
            config = json.load(f)

        salt = base64.b64decode(config['salt'])
        iterations = int(config.get('iterations', 100000))

        kek = cls._derive_kek_static(password, salt, iterations)
        fernet_kek = Fernet(kek)
        dek = fernet_kek.decrypt(config['dek_by_password'].encode())

        mgr = cls(dek)
        mgr.password = password
        mgr.salt = salt
        mgr.iterations = iterations
        return mgr

    @staticmethod
    def _derive_kek_static(password: str, salt: bytes, iterations: int) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data: str) -> bytes:
        """Шифрует строку"""
        return self.fernet.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """Расшифровывает данные"""
        return self.fernet.decrypt(encrypted_data).decode()

    def encrypt_to_file(self, data: str, file_path: Path):
        """Шифрует и сохраняет данные в файл"""
        encrypted_data = self.encrypt(data)
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

    def decrypt_file(self, file_path: Path) -> str:
        """Читает и расшифровывает файл"""
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
        return self.decrypt(encrypted_data)

    @classmethod
    def create_new(cls, password: str, config_path: Path, iterations: int = 200_000):
        """Создаёт новый DEK, оборачивает его паролем и DPAPI, сохраняет конфиг и возвращает менеджер."""
        # Случайный DEK (ключ Fernet)
        dek = Fernet.generate_key()

        # Парольное оборачивание (KEK)
        salt = os.urandom(16)
        kek = cls._derive_kek_static(password, salt, iterations)
        dek_by_password = Fernet(kek).encrypt(dek).decode()

        # DPAPI оборачивание для фоновой записи
        dek_by_dpapi = base64.b64encode(win32crypt.CryptProtectData(dek, 'KeyDairy-DEK', None, None, None, 0)).decode()

        config = {
            'salt': base64.b64encode(salt).decode(),
            'iterations': iterations,
            'dek_by_password': dek_by_password,
            'dek_by_dpapi': dek_by_dpapi
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        mgr = cls(dek)
        mgr.password = password
        mgr.salt = salt
        mgr.iterations = iterations
        return mgr

    def verify_password(self, config_path: Path) -> bool:
        """Проверяет пароль, пытаясь расшифровать DEK, обёрнутый паролем."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            salt = base64.b64decode(config['salt'])
            iterations = int(config.get('iterations', 100000))
            kek = self._derive_kek_static(self.password, salt, iterations)
            Fernet(kek).decrypt(config['dek_by_password'].encode())
            return True
        except Exception:
            return False

    def change_password(self, new_password: str, config_path: Path):
        """Меняет только обёртку пароля для существующего DEK. Логи не трогаем."""
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Достаём текущий DEK: используем DPAPI-вариант
        dek = win32crypt.CryptUnprotectData(base64.b64decode(config['dek_by_dpapi']), None, None, None, 0)[1]

        # Новая обёртка пароля
        salt = os.urandom(16)
        iterations = int(config.get('iterations', 200000))
        kek = self._derive_kek_static(new_password, salt, iterations)
        dek_by_password = Fernet(kek).encrypt(dek).decode()

        config.update({
            'salt': base64.b64encode(salt).decode(),
            'iterations': iterations,
            'dek_by_password': dek_by_password
        })

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Обновляем текущий менеджер на новый пароль
        self.password = new_password
