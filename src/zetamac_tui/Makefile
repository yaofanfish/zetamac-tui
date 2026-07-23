
BINARY_NAME=my_textual_app

all: build

build:
	python -m nuitka \
		--standalone \
		--onefile \
		--include-package=textual \
		--include-package=rich \
		--include-data-files=*.tcss=./ \
		--assume-yes-for-downloads \
		--output-filename=$(BINARY_NAME) \
		main.py

clean:
	rm -rf *.build *.dist *.onefile-build $(BINARY_NAME).bin $(BINARY_NAME).exe

