import pathlib

import regex as re
import requests
from bs4 import BeautifulSoup


def get_text(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.find("div", {"class": "main_text"}).text
    file_path_name = "吾輩は猫である.txt"
    file_path = pathlib.Path(file_path_name).absolute()
    with open(file_path, "w") as f:
        f.write(text)
    return file_path


def get_idiom(text):
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    pattern = r"\p{Script=Han}{4}(?!\p{Script=Han})"
    matches = re.findall(pattern, text)
    print(matches)
    print(len(matches))
    unique_matches = list(set(matches))
    match_count = len(unique_matches)
    print(match_count)
    return None


def get_longest_idiom(text):
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    pattern = r"\p{Script=Han}+"
    matches = re.findall(pattern, text)
    max_len = max([len(match) for match in matches])
    longest_words = [match for match in matches if len(match) == max_len]
    print(
        "最長の熟語は{}文字で、その熟語は：{}".format(max_len, "、".join(longest_words))
    )
    return None


if __name__ == "__main__":
    url = "https://www.aozora.gr.jp/cards/000148/files/789_14547.html"
    path = get_text(url)
    with open(path, "r") as f:
        text = f.read()
    get_idiom(text)
    get_longest_idiom(text)
