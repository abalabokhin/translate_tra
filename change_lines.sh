 #!/bin/bash
while read line; do 
IFS=',' read -r -a array <<< $line
echo $line ${array[0]} ${array[1]}
#find . ! -iname '_' ! -iname '*.tra.ascii.bak' ! -iname '*.tra' ! -name "lines.txt" -exec grep -lIs $line {} \; -print
find . \( -iname '*.d' -or -iname '*.tph' -or -iname '*.baf' \) -exec sed -i "s/${array[0]}\b/${array[1]}/g" {} +
done < lines_to_change.txt
