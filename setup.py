from setuptools import setup

APP = ['main.py']
APP_NAME = 'CAN_Library_Generator'
#DATA_FILES = ['src/png']
OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'tkinter',
        'PIL',
        'sv_ttk',
        'cantools',
        'darkdetect',
        'bitstruct',
        'crccheck',
        'ttkbootstrap',
        'ttkwidgets',
        'textparser'
    ],
    'includes': [
        'PIL',
        'tkinter',
        'sv_ttk',
        'cantools',
        'darkdetect',
        'bitstruct',
        'crccheck',
        'ttkbootstrap',
        'ttkwidgets',
        'textparser'
    ],
    'resources': ['src/png']
    #'iconfile': 'ico/muj_icon.icns',
}

setup(
    app=APP,
    name=APP_NAME,
    #data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)