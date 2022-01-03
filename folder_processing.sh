#!/bin/bash
find "$1" -iname "*.tra" -exec python3 translate_tra.py --no-add-prefix --engine=googlecloud {} \;
