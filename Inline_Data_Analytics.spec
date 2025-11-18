# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons', 'icons'),  # Include icons folder if it exists
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport',
        
        # Data processing
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.testing',
        'numpy.testing._private',
        
        # Scientific computing
        'scipy',
        'scipy.signal',
        'scipy.ndimage',
        'scipy.special',
        'scipy.special._ufuncs_cxx',
        'scipy.interpolate',
        'scipy.stats',
        'scipy.stats._stats_py',
        'scipy.sparse',
        'scipy.sparse._base',
        'scipy._lib',
        'scipy._lib._util',
        'scipy._lib.array_api_compat',
        
        # Standard library (needed by scipy)
        'unittest',
        'unittest.mock',
        
        # Plotting
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.figure',
        'matplotlib.colors',
        'mplcursors',
        
        # Excel support
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.cell._writer',
        'xlrd',
        
        # File handling
        'nptdms',
        'chardet',
        
        # Optional - for advanced smoothing
        'statsmodels',
        'statsmodels.nonparametric',
        'statsmodels.nonparametric.smoothers_lowess',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',  # Exclude if not used
        # Removed 'unittest' from here - scipy needs it!
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Inline_Data_Analytics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add 'icon.ico' if you have an icon file
)
