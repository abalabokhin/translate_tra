# translate_tra
The script to translate one \*.tra file (a localization file for infinity engine modding) using google translate.

The script should be used like this:
```
python3 translate_tra.py infile.tra
```
See usage (--usage) for details.

Make sure you install argparse and textblob python libraries: 
```
pip install argparse
pip install textblob
```
Translating with google translate has some limitations for request number. To avoid them the delay is added (I am not sure it works, actually, more testing needs to be done). Anyway, now script works very slow (1 second delay between requests). If you see an exception: "Too Many Requests", you should stop using the script for a day (the requests limit is reset every day).
