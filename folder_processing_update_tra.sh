#!/bin/bash
#ATTENTION! The original files will be replaces with updated ones!
#$1 dir with files to adapt translation
#$2 source-dir
#$3 translated-dir
find "$1" -iname "*.tra" -exec python3 ./update_tra.py --out {} --source-dir "$2" --translated-dir "$3" {} \;
