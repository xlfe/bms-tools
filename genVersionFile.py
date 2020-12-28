#!/usr/bin/env python

import subprocess
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

if __name__ == '__main__':
    genVersionFile()