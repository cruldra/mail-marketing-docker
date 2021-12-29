import requests
from pathlib import Path


def my_ip():
    response = requests.request("GET", "https://api.ipify.org/")
    return response.text


def read_file_content(path):
    return Path(path).read_text()


def write_content_to_file(path, text):
    Path(path).write_text(text)


def indices(arr, predicate=lambda x: bool(x)):
    return [i for i, x in enumerate(arr) if predicate(x)]
