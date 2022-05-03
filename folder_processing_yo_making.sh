#!/bin/bash
find "$1" -iname "*.tra" -exec python3 yo_making.py {} \;
