#
# Top-level OCCAM razor Makefile
#
# To use:
#
#  set LLVM_HOME to the install directory of LLVM
#  set OCCAM_HOME to where you want the occam shared library to live.
#
# Then type make, followed make install (or sudo -E make install).
#

ifneq (,)
This Makefile requires GNU Make.
endif

# tools that are used
PROTOC  = $(shell which protoc)
PYLINT  = $(shell which pylint)
MKDIR_P = mkdir -p
RM_F    = rm -f

export OCCAM_LIB = $(OCCAM_HOME)/lib
export OCCAM_BIN = $(OCCAM_HOME)/bin

# tests needs an LLVM install from cmake with:
# -DLLVM_INSTALL_UTILS=ON
# https://bugs.llvm.org//show_bug.cgi?id=25675

all: sanity_check dist occam_lib

#
# Sanity Checks.
#
# iam: We do not really need protoc if we add the generated code to the repo.
# But currently we do not do that in the python, but do do it in the  C++, so some
# consistency would be good.
#
#
sanity_check:  occam_home  llvm_home

occam_home:
ifeq ($(OCCAM_HOME),)
	$(error OCCAM_HOME is undefined)
endif
	$(MKDIR_P) $(OCCAM_LIB)
	$(MKDIR_P) $(OCCAM_BIN)

llvm_home:
ifeq ($(LLVM_HOME),)
	$(error LLVM_HOME is undefined)
endif

#iam: run this if certain files are not there
submodule_update:
	git submodule update --remote --init --recursive

# easier on the fingers
update: submodule_update



occam_lib:
	$(MAKE) -C src all

.PHONY: test
test:
	$(MAKE) -C test test

install_occam_lib: occam_lib
	$(MAKE) -C src install

uninstall_occam_lib:
	$(MAKE) -C src uninstall_occam_lib


install_razor:  dist
	pip3 install .

uninstall_razor:
ifeq ($(PROTOC),)
	$(error uninstalling razor requires pip)
endif
	pip3 uninstall razor

uninstall: uninstall_razor uninstall_occam_lib

install: install_occam_lib install_razor

#spanish people are too impatient to do the "pip install ." more than once.
instalar: install_occam_lib #install_razor




#iam: local editable install of razor for developing
develop: install_occam_lib
	pip3 install -e .

# python pip packaging

dist: proto
	python3 setup.py sdist bdist_wheel

proto:  protoc
	mkdir -p razor/proto
	touch razor/proto/__init__.py
	$(PROTOC) --proto_path=src --python_out=razor/proto src/Previrt.proto

protoc:
ifeq ($(PROTOC),)
	$(error google protobuffer compiler "protoc" required)
endif

#
# Note Bene:
#
# If you need to publish a new pip version you must
# change the version number in razor/version.py,
# otherwise the server will give you an error.

publish: dist
	python3 -m twine upload dist/*

lint:
ifeq ($(PYLINT),)
	$(error lint target requires pylint)
endif
# for detecting more than just errors:
	@ $(PYLINT) --rcfile=.pylintrc razor/*.py
#	@ $(PYLINT) -E razor/*.py

md2rst:
	pandoc --from=markdown --to=rst --output=README.rst README.md

zippity:
	rm -rf doczip*; mkdir doczip;
	cat README.md | pandoc -f markdown_github > doczip/index.html
	zip -r -j doczip.zip doczip

limpio:
	$(MAKE) -C src clean
	$(MAKE) -C test clean
	$(MAKE) -C examples clean

clean: limpio
	rm -rf razor/proto
	rm -rf dist
	rm -f lib/*
	rm -f bin/*

.PHONY: clean
