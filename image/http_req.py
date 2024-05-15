from pprint import pprint

import requests


def detect_language(text):
    url = "http://127.0.0.1:5000/detect"
    params = {"q": text}
    response = requests.post(url, data=params)
    print(response.json())
    return response.json()


def translate_text(text, dest):
    url = "http://127.0.0.1:5000/translate"
    params = {"q": text, "source": "auto", "target": dest, "format": "text"}
    response = requests.post(url, data=params)
    return response.json()


if __name__ == "__main__":
    # テキストの各部分を個別に識別して翻訳する
    # Mount Fuji is the highest mountain in Japan
    # a main Japanese castle is Tokyo Mont Blanc is the highest mountain in Europe?
    # what is the country's capital city where the highest mountain in the world is located?
    r = "O Monte Fuji é a montanha mais alta do Japão a glavni grad Japana je Tokio Mont Blanc je najvišja gora v Evropi ano ang kabiserang lungsod ng bansa kung saan matatagpuan ang pinakamataas na bundok sa mundo?"
    texts = "ano ang kabiserang lungsod ng bansa kung saan matatagpuan ang pinakamataas na bundok sa mundo"
    translations = []
    languages = []
    lang = detect_language(texts)[0]["language"]
    languages.append(lang)
    translated_text = translate_text(texts, "en")
    translations.append(translated_text["translatedText"])
    print(translations)
