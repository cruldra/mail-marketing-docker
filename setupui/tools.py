import socket

import httpx
import requests
from pathlib import Path

import rich


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


def download_file(url, dist):
    with open(dist, "w") as download_file:
        with httpx.stream("GET", url) as response:
            total = int(response.headers["Content-Length"])
            with rich.progress.Progress(
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    rich.progress.BarColumn(bar_width=None),
                    rich.progress.DownloadColumn(),
                    rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task("Download", total=total)
                for chunk in response.iter_bytes():
                    download_file.write(chunk.decode('utf-8'))
                    progress.update(download_task, completed=response.num_bytes_downloaded)


def check_remote_port_opened(host, port) -> bool:
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = (host, port)
    result_of_check = a_socket.connect_ex(location)
    res = result_of_check == 0
    a_socket.close()
    return res


if __name__ == '__main__':
    print(check_remote_port_opened("34.92.191.73", 25))
