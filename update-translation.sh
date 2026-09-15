#!/bin/bash
set -e
xgettext -o po/eta-remote.pot --from-code="utf-8" \
     -f <(find src -type f -iname "*.py" -o -iname "*.js")
for file in po/*.po; do
    msgmerge $file po/eta-remote.pot -o $file.new
    echo POT: $file
    rm -f $file
    mv $file.new $file
done
