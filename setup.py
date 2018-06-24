from setuptools import setup

setup(
    name = 'hugo-gui',
    version = '0.0.1',
    url = 'https://github.com/mortbauer/hugo_gui.git',
    author = 'Martin Ortbauer',
    author_email = 'mortbauer@gmail.com',
    description = 'A pyqt frontend for hugo static blog generator',
    install_requires=['appdirs','sh','pyyaml','PyQt5'],
    entry_points={
        'console_scripts': ['hugo-gui=main:main'],
    },
)
