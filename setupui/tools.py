import socket

import requests
from pathlib import Path


def my_ip():
    response = requests.request("GET", "https://api.ipify.org/")
    return response.text


def read_file_content(path):
    path = Path(path)
    path.name
    return Path(path).read_text()


def write_content_to_file(path, text):
    Path(path).write_text(text)


def indices(arr, predicate=lambda x: bool(x)):
    return [i for i, x in enumerate(arr) if predicate(x)]


def check_remote_port_opened(host, port) -> bool:
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = (host, port)
    result_of_check = a_socket.connect_ex(location)
    res = result_of_check == 0
    a_socket.close()
    return res


if __name__ == '__main__':
    print(check_remote_port_opened("34.92.191.73", 25))
