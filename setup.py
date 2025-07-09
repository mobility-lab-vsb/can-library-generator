from setuptools import setup

APP = ['main.py']
APP_NAME = 'CAN_Library_Generator'
DATA_FILES = ['png']
OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'tkinter',
        'PIL',        # pillow
        'sv_ttk',
        'cantools',
        'darkdetect',
        'bitstruct',
        'crccheck',
        'python-can', # corresponds to python-can
        'ttkbootstrap',
        'ttkwidgets',
        'textparser'
    ],
    # 'iconfile': 'ico/muj_icon.icns',
    'includes': [
        'PIL',        # pillow
        'tkinter',
        'sv_ttk',
        'cantools',
        'darkdetect',
        'bitstruct',
        'crccheck',
        'python-can', # corresponds to python-can
        'ttkbootstrap',
        'ttkwidgets',
        'textparser'
    ]
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)