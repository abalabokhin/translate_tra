# translate_tra
The script to translate one \*.tra file (a localization file for infinity engine modding) using google translate.

The script should be used like this:
```
python3 translate_tra.py infile.tra
```
See usage (--help) for details.

Make sure you install argparse and textblob python libraries: 
```
pip install googletrans==4.0.0rc1
pip install textblob
```
Translating with Google Translate has some limitations for request number. To avoid them googletrans library can be used.
To translate using this library you can use "--experimental" option. However, the translation seems to be
worse with googletrans library (more comparisson needs to be done).

If you use non-experimental mode, you can see an exception: "Too Many Requests".
In this case you should stop using the script for a day (the requests limit is reset every day).
