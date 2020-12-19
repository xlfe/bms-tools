#!/usr/bin/env python

# BMS Tools
# Copyright (C) 2020 Eric Poulsen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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