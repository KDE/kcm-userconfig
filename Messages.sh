#!/bin/sh
$EXTRACTRC ui/*.ui >> ./ui.py || exit 11
$XGETTEXT --language=Python *.py -o $podir/userconfig.pot
rm -f ui.py
