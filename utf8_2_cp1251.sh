#!/bin/bash
mkdir cp1251
for a in $(find . -iname "*.tra"); do iconv -f utf-8 -t cp1251 <"$a" >cp1251/"$a" ; done
