#!/bin/python3

#copy it into the directory with many rar files and run it
#it will extract them all in corresponding directories

import os
import subprocess 
#This is to get the directory that the program 
# is currently running in.
dir_path = os.path.dirname(os.path.realpath(__file__))
for root, dirs, files in os.walk(dir_path):
    for file in files: 
        if file.endswith('.rar'):
            file = root+'/'+str(file)
            dir,_ = os.path.splitext(file)
            print(file, dir)
            os.makedirs(dir, exist_ok=True)
            subprocess.run(["unrar", "x", file, dir])
            

