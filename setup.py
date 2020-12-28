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
import subprocess
import argparse
import sys
import os

scriptFile = os.path.abspath(__file__)
scriptDir = os.path.dirname(scriptFile)

def genVersionFile():
    cmd = 'git describe --long --dirty --abbrev=10 --tags'.split()
    version = subprocess.check_output(cmd, cwd = scriptDir).strip()
    fn = os.path.join(scriptDir, 'bmstools', 'version.py')
    with open(fn, 'w') as v:
        v.write(f'''#!/usr/bin/env python

version = {repr(str(version, 'utf-8'))}
''')
    return version


def doSetup():
    setup(
        name='bmstools',
        url='https://gitlab.com/MrSurly/bms-tools.git',
        maintainer='Eric Poulsen',
        maintainer_email='"Eric Poulsen" <eric@zyxod.com>',
        version='0.0.1-dev',
        install_requires=['pyserial~=3.4', 'openpyxl~=3.0.5', 'xlsxwriter==1.3.7'],

        extras_require = {
            'gui': ['wxPython~=4.1.1', 'pyinstaller']
        },
        license='Creative Commons Attribution-Noncommercial-Share Alike license',
        packages=['bmstools'],
        entry_points = {
            'console_scripts': [
            ]
        }
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--bmstools-gen-version', action = 'store_true')

    n = sys.argv[0]
    args, rem = p.parse_known_args()
    sys.argv = [n] + rem
    ver = genVersionFile()
    if args.bmstools_gen_version:
        print(f'version is {ver}')
    else:
        doSetup()
