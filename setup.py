#!/usr/bin/env python

from distutils.core import setup

setup(
    name='bmstools',
    url='https://gitlab.com/MrSurly/bms-tools.git',
    maintainer='Eric Poulsen',
    maintainer_email='"Eric Poulsen" <eric@zyxod.com',
    version='0.0.1-dev',
    install_requires=[
        'pyserial~=3.4', 
        ],
    extras_require = {
        'gui': ['wxPython~=4.1.1']
    },
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    packages=['bmstools'],
    entry_points = {
        'console_scripts': [
        ]
    }
)