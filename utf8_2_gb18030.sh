#!/bin/bash
mkdir gb18030
for a in $(find . -iname "*.tra"); do iconv -f utf-8 -t GB18030 <"$a" >gb18030/"$a" ; done
