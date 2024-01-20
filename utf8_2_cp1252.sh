#!/bin/bash
mkdir cp1252
for a in $(find . -iname "*.tra"); do iconv -f utf-8 -t cp1252 <"$a" >cp1252/"$a" ; done
