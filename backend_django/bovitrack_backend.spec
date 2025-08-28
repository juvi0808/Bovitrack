# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['live_stock_manager/wsgi.py'],
    pathex=[],
    binaries=[],
    datas=[
        # --- FIX: Tell PyInstaller to include your entire 'api' and 'live_stock_manager' apps ---
        ('api', 'api'),
        ('live_stock_manager', 'live_stock_manager')
    ],
    hiddenimports=[
        # --- FIX: Explicitly include modules that PyInstaller might miss ---
        'rest_framework',
        'corsheaders',
        'api.apps.ApiConfig' # Helps Django find your app
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='bovitrack_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep this True for debugging, change to False for final release to hide the console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bovitrack_backend',
)
