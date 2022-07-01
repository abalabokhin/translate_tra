 #!/bin/bash
while read line; do 
IFS=',' read -r -a array <<< $line
echo ${array[0]}
find . \( -iname '*.d' -or -iname '*.tph' -or -iname '*.baf' \) -exec grep -lIs ${array[0]} {} \; -print
done < lines_to_change.txt
