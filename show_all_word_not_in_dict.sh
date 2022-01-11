#!/bin/bash
a=`find -name "*.tra" -exec hunspell -d ru_RU -l {} \; | sort -u`
for s in $a
do
	b=`grep "\b$s\b" *.tra | tr -d '\n'`
	echo "$s $b"
done
