# translate_tra
There are many scripts here, but the main one:

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
pip install google-cloud-translate
```

There are 3 translation engine are used:
* googletrans - free and no limitations per requests, but the translation quality is bad.
* textblob - free, has a good translation quality but has some limited number of requests. 
If you see a message: "Too Many Requests. ...", you should wait for another day before using this engine again.
* googlecloud - official google cloud engine with the best possible translation quality 
  (not a big difference with textblob engine though). To use this engine you should create 
  a project in google cloud, be authenticated there and google can actually charge some money from you.

You can select engine with e.g "--engine=googletrans". By default textblob is used.
