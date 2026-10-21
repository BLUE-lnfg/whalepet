# -*- mode: python ; coding: utf-8 -*-
import os

# SPECPATH 由 PyInstaller 注入，等于 spec 文件所在目录（即 D:\Projects\whalepet）
root_dir = SPECPATH

a = Analysis(
    ['main.py'],
    pathex=[root_dir],
    binaries=[],
    datas=[
        # 打包整个 profiles（含 .cache 帧序列和素材），让 PyInstaller 直接跑也能用
        ('profiles', 'profiles'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtMultimedia',
        'shiboken6',
        'app.config.manager',
        'app.behavior.voice_behavior',
        'app.behavior.wander',
        'app.ui.settings_dialog',
        'app.services.autostart',
        'app.services.theme',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.Qt3DCore',
        'PySide6.QtQuick',
        'PySide6.QtQml',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WhalePet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WhalePet',
)