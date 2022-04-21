#!/bin/bash
a=`find -iname "*.tra" -exec hunspell -d ru_RU -l {} \; | sort -u`
for s in $a
do
	b=`grep "\b$s\b" *.[t,T][r,R][a,A] | tr -d '\n'`
	echo "$s $b"
done
