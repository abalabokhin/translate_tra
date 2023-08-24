import deepl

file = open('DEEPL_API_KEY', mode='r')
deepl_key = file.read().rstrip()
translator = deepl.Translator(deepl_key)

entries = {"Faerun": "Фаэрун"}

my_glossary = translator.create_glossary(
    "My glossary",
    source_lang="EN",
    target_lang="RU",
    entries=entries,
)

translated_string = str(translator.translate_text("Faerun", target_lang='ru', source_lang='en', glossary=my_glossary))
print(translated_string)

