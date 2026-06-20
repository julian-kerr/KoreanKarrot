import time
import requests
import xml.etree.ElementTree as ET

from hangul_romanize import Transliter
from hangul_romanize.rule import academic

transliter = Transliter(academic)

API_KEY = "10C0546A14DB2730C63BC2E0E08022A5"


def lookup_word(word):
    url = "http://krdict.korean.go.kr/api/search"

    params = {
        "key": API_KEY,
        "q": word,
        "translated": "y",
        "trans_lang": "1"
    }

    last_error = None

    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            print(response.text)

            root = ET.fromstring(response.text)

            item = root.find(".//item")
            if item is None:
                return None

            return {
                "word": item.findtext("word"),
                "pronunciation": item.findtext("pronunciation"),
                "romanization": transliter.translit(
                    item.findtext("pronunciation") or item.findtext("word") or ""
                ),
                "pos": item.findtext("pos"),
                "level": item.findtext("word_grade"),
                "meaning": item.findtext(".//trans_word"),
                "definition": item.findtext(".//trans_dfn"),
                "link": item.findtext("link")
            }

        except Exception as e:
            last_error = e
            time.sleep(1)

    print("KRDict lookup failed:", last_error)
    return None


if __name__ == "__main__":
    print(lookup_word("진짜"))