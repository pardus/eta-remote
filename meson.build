project('eta-remote', 'c')

deps = [
    dependency('x11'),
    dependency('xext'),
]

lib= library(
    'capture',
    ['src/client/X11/capture.c'],
    dependencies: deps,
    install_dir:  get_option('prefix') / 'share/eta/eta-remote/client/X11'
)

install_subdir(
    'src',
    install_dir: get_option('prefix') / 'share/eta/eta-remote',
    strip_directory: true
)
