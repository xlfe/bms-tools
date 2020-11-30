# BMS Tools

## Purpose
This repository aims to provide open source tools for popular Battery Management Systems (BMS).  

## Support
Currently it only supports the [JBD](https://www.lithiumbatterypcb.com/) BMS.

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

The GUI build uses [pyinstaller](https://www.lithiumbatterypcb.com/), and as such can only build an executable for the OS type it's built on; no cross-compilation.

1. `pip install .[gui]`
1. make








