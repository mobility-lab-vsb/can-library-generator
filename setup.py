from setuptools import setup

APP = ['main.py']
APP_NAME = 'CAN_Library_Generator'
DATA_FILES = ['png']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'PIL', 'sv_ttk', 'ttkwidget', 'cantools', 'darkdetect'],
    # 'iconfile': 'ico/muj_icon.icns',
    'includes': ['PIL', 'tkinter', 'sv_ttk', 'ttkwidget', 'cantools', 'darkdetect']
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)