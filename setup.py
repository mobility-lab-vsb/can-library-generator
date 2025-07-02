from setuptools import setup

APP = ['main.py']
DATA_FILES = ['png']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'PIL', 'sv_ttk', 'ttkwidget', 'cantools', 'darkdetect'],
    # 'iconfile': 'ico/muj_icon.icns',  # pokud máš ikonu pro mac
    'includes': ['PIL', 'tkinter', 'sv_ttk', 'ttkwidget', 'cantools', 'darkdetect']
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

# pip install py2app
# python setup.py py2app

# brew install create-dmg
# create-dmg dist/main.app