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

def get_all_translation(lang="en"):
    mo_file = os.path.join(TRANSLATIONS_PATH, lang, "LC_MESSAGES", f"{APPNAME}.mo")
    if not os.path.exists(mo_file):
        mo_file = os.path.join(TRANSLATIONS_PATH, lang.split("_")[0].split("-")[0], "LC_MESSAGES", f"{APPNAME}.mo")

    if os.path.exists(mo_file):
        with open(mo_file, "rb") as f:
            catalog = gettext.GNUTranslations(f)._catalog
            return {msgid: msgstr for msgid, msgstr in catalog.items() if msgid}

    return {}
