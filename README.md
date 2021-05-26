# translate_tra
The script to translate one \*.tra file (a localization file for infinity engine modding) using google translate.

The script should be used like this:
```
python3 translate_tra.py infile.tra
```
See usage (--help) for details.

Make sure you install all the necessary python libraries: 
```
pip install googletrans==4.0.0rc1
pip install textblob
pip install pycld2
```
Translating with TextBlob has some limitations for request number, but it is much more accurate (as it is now) than 
googletrans library. The language is detected offline with cld2 library to reduce number of requests to with TextBlob.
If you see a message: "Too Many Requests. ...", you should probably wait for another day or a month or a year 
before using the application again.
