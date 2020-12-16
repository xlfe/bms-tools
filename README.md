# BMS Tools

## Purpose
This repository aims to provide open source tools for popular Battery Management Systems (BMS).  

## Support
Currently it only supports the [JBD](https://www.lithiumbatterypcb.com/) BMS.

I've compiled some [JDB register documentation](JDB_REGISTER_MAP.md), and at the time of this writing the most complete that I could find.

## Code

Currently provided:

* Backend Python library 
* Frontent GUI App

Planned:

* Command line app

## Installation

### Backend Library

`pip install .`

### GUI Build

While the GUI itself is wxpython and doesn't technically _need_ to be built, but for distribution 
 [pyinstaller](https://www.pyinstaller.org/) is used to build a distributable executable.

1. `pip install .[gui]`
1. make








