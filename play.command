#!/bin/bash
# Double-click in Finder to open Terminal and play.
cd "$(dirname "$0")" || exit 1
printf '\e[8;34;110t'   # ask Terminal for a 110x34 window
exec python3 -m asciiparticle "$@"
