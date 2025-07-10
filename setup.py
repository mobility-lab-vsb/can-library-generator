from setuptools import setup
import os

def find_data_files(source, target):
    data_files = []
    for dirpath, _, filenames in os.walk(source):
        files = []
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            files.append(full_path)
        if files:
            target_path = os.path.join(target, os.path.relpath(dirpath, source))
            data_files.append((target_path, files))
    return data_files


APP = ['main.py']
APP_NAME = 'CAN_Library_Generator'
#DATA_FILES = ['src/png']
DATA_FILES = find_data_files('src/png', 'src/png')
print(DATA_FILES)
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
    ]
    #'iconfile': 'ico/muj_icon.icns',
}

setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)