# Инструкция по сборке KeyDairy в исполняемый файл

## Установка PyInstaller

```bash
pip install pyinstaller
```

## Сборка основного приложения

```bash
pyinstaller --onefile --windowed --icon=icon.ico main_keylogger.py
```

## Альтернативная сборка с дополнительными параметрами

```bash
pyinstaller ^
    --onefile ^
    --windowed ^
    --hidden-import=log_viewer ^
    --hidden-import=encryption_utils ^
    --hidden-import=PIL ^
    --hidden-import=pystray ^
    --hidden-import=pynput ^
    --add-data="icon.ico;." ^
    --icon=icon.ico ^
    main_keylogger.py
```

## Создание spec файла для продвинутой настройки

Создайте файл `keydairy.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_keylogger.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],
    hiddenimports=[
        'log_viewer',
        'encryption_utils', 
        'PIL._tkinter_finder',
        'pystray._win32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KeyDairy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
```

Затем:

```bash
pyinstaller keydairy.spec
```

## Результат

Исполняемый файл будет создан в папке `dist/`
