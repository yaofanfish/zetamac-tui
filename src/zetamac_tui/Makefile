
BINARY_NAME=nuitka_exe

all: build

build:
	python -m nuitka \
		--standalone \
		--onefile \
		--include-package=textual \
		--include-package=rich \
		--assume-yes-for-downloads \
		--output-filename=$(BINARY_NAME) \
		main.py

clean:
	rm -rf *.build *.dist *.onefile-build $(BINARY_NAME).bin $(BINARY_NAME).exe

