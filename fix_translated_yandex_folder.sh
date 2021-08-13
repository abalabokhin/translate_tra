#!/bin/bash
find "$1" -iname "*.tra" -exec  sed -i 's/<ИМ[^>]*>/<CHARNAME>/g' {} \;
