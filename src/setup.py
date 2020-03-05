from coderman import app_version
from setuptools import setup

setup(
    name='coderman',
    version=app_version,
    py_modules=['coderman'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        coderman=coderman:main
    ''',
)
