#!/bin/bash
find "$1" -iname "*.tra" -printf '%f\t%p\n' | sort -V -k1 | cut -d$'\t' -f2 | tr '\n' '\0' | xargs -r0 -I {} python3 ./yo_making.py "{}"
