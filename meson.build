project('eta-remote', 'c')

deps = [
    dependency('x11'),
    dependency('xext'),
]

subdir('po')

lib= library(
    'capture',
    ['src/client/X11/capture.c'],
    install: true,
    dependencies: deps,
    install_dir:  get_option('datadir') / 'eta/eta-remote/client/X11'
)

install_subdir(
    'src',
    install_dir: get_option('datadir') / 'eta/eta-remote',
    strip_directory: true
)

install_data(
    'data/eta-remote-autostart.desktop',
    install_dir: get_option('sysconfdir') / 'xdg/autostart',
    rename: 'tr.org.pardus.eta-remote.desktop'
)

install_data(
    'data/config.json',
    install_dir: get_option('sysconfdir') / 'pardus',
    rename: 'eta-remote.json'
)

install_data(
    'data/eta-remote.desktop',
    install_dir: get_option('datadir') / 'applications',
    rename: 'tr.org.pardus.eta-remote.desktop'
)

install_data(
    'data/org.pardus.eta-remote.uinput.policy',
    install_dir: get_option('datadir') / 'polkit-1/actions'
)

install_data(
    'data/org.pardus.eta-remote.gschema.xml',
    install_dir: get_option('datadir') / 'glib-2.0/schemas'
)

install_data(
    'data/icons/tr.org.pardus.eta-remote.svg',
    install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)

install_data(
    'data/icons/tr.org.pardus.eta-remote-started.svg',
    install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)

install_data(
    'data/icons/tr.org.pardus.eta-remote-stopped.svg',
    install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)

conf = configuration_data()
conf.set('PREFIX', get_option('prefix'))

eta_remote_main = configure_file(
  input: 'eta-remote.c.in',
  output : 'eta-remote.c',
  configuration: conf,
)


py_mod = import('python')
py = py_mod.find_installation('python3')

if not py.version().version_compare('>=3.8')
  error('Python 3.8 or newer is required; found ' + py.version())
endif


py_deps = [py.dependency(), py.dependency(embed: true)]



executable(
  'eta-remote',
  eta_remote_main,
  dependencies: py_deps,
  install: true,
  install_dir: get_option('bindir')
)