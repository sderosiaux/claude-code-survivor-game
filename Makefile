.PHONY: build clean play

build:
	pyinstaller --onefile verify.py
	mv dist/verify ./verify
	rm -rf build dist verify.spec
	rm verify.py

clean:
	rm -f verify
	rm -rf .audit state.json

play: build
	./verify init
