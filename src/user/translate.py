import os
import sys

sys.path.insert(0, os.path.dirname(__file__)+"/../")

from i18n import _, get_all_translation

translate = get_all_translation()

def gen_translate():
    ctx = """function _(msg){\n"""
    for key in translate.keys():
        key = key.replace("\\", "\\\\").replace("\"", "\\\"")
        ctx += "    if(msg == \"{}\") return \"{}\";\n".format(key, _(key))
    ctx += "    return msg;\n"
    ctx += "}\n"
    return ctx;

if __name__ == "__main__":
    print(gen_translate())
