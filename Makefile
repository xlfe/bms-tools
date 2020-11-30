.ONESHELL:
.PHONY: build clean all
.SILENT:
SHELL=/usr/bin/bash
WINDOWED=--windowed
ONEFILE=--onefile

NAME=bms_utils_jbd

all: gui

gui:
	if [[ "$$OSTYPE" == "linux-gnu" ]]; then
		echo Linux build ...
		export PATHSEP=":"
	else
		echo Windows build ...
		export PATHSEP=";"
	fi
	pyinstaller.exe jbd_gui.py --noconfirm ${WINDOWED} ${ONEFILE} --icon "img/batt_icon_128.ico" --add-data "img$${PATHSEP}img" -n bms_utils_jbd

clean:
	rm -Rf build dist