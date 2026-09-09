# Eta Remote

## Run from source
```sh
meson setup build
ninja -C build
glib-compile-schemas ./data
python3 -m src # for headless
python3 src/MainWindow.py # for gui
```

