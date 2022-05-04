#!/bin/bash
find "$1" -iname "*.tra" -print0 | sort -zn | xargs python3 yo_making.py
