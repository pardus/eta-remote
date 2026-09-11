import gettext
import locale
import os

APPNAME = "eta-remote"
TRANSLATIONS_PATH = "/usr/share/locale"

try:
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    locale.textdomain(APPNAME)
    gettext.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME)
    _ = gettext.gettext
except Exception:
    def _(msg):
        return msg
