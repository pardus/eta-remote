all: clean build

build:
	gcc -o client/X11/libcapture.so client/X11/capture.c $(shell pkgconf --cflags --libs x11 xext) -shared

clean:
	rm -f client/X11/libcapture.so || true
	find -type d -iname "__pycache__" | sed "s/^/rm -rf /g" | sh -x