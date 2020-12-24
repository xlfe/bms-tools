.ONESHELL:
.PHONY: build clean all debug
.SILENT:
SHELL=/bin/bash
WINDOWED=--windowed
ONEFILE=--onefile

NAME=bms_utils_jbd

COMMIT_HASH=$(shell git describe --long --dirty --abbrev=10 --tags)
COMMIT_HASH_PYTHON=commit_hash.py
DIRTY=$(findstring, dirty, $(COMMIT_HASH))
EXACT_TAG:=$(if $(DIRTY),,$(shell git tag --points-at HEAD))

all: gui

$(COMMIT_HASH_PYTHON):
	echo \#!/usr/bin/env python > $@
	echo commit_hash = \'$(COMMIT_HASH)\' >> $@
	echo tag = \'$(EXACT_TAG)\' >> $@

gui: $(COMMIT_HASH_PYTHON)
	if [[ "$$OSTYPE" == "linux-gnu" ]]; then
		echo Linux build ...
		export OS_NAME='linux'
		export PATHSEP=":"
		export PYINSTALLER='pyinstaller'
	else
		echo Windows build ...
		export OS_NAME='windows'
		export PATHSEP=";"
		export PYINSTALLER='pyinstaller.exe'
	fi
	$${PYINSTALLER} jbd_gui.py --noconfirm ${WINDOWED} ${ONEFILE} --icon "img/batt_icon_128.ico" --add-data "img$${PATHSEP}img" -n bms_tools_jbd_$${OS_NAME}_$(if $(EXACT_TAG),$(EXACT_TAG),$(COMMIT_HASH))
	rm $(COMMIT_HASH_PYTHON)

clean:
	- rm -Rf build dist *.spec
	- find -iname __pycache__ -exec rm -Rf {} \;

debug:
	echo EXACT_TAG: \"$(EXACT_TAG)\"
	echo DIRTY: \"$(DIRTY)\"
	echo COMMIT_HASH: \"$(COMMIT_HASH)\"