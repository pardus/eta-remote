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

def get_all_translation():
    current_lang = os.environ.get('LANG', 'en')
    current_lang = current_lang.split('.')[0].split('_')[0]

    mo_file = os.path.join(TRANSLATIONS_PATH, current_lang, "LC_MESSAGES", f"{APPNAME}.mo")
    if os.path.exists(mo_file):
        with open(mo_file, "rb") as f:
            catalog = gettext.GNUTranslations(f)._catalog
            return {msgid: msgstr for msgid, msgstr in catalog.items() if msgid}

    return {}
