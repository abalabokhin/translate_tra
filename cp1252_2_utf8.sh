#!/bin/bash
mkdir utf8
for a in $(find . -iname "*.tra"); do iconv -f cp1252 -t utf-8 <"$a" >utf8/"$a" ; done
