import json
import os
import re
import socket

import docker
import httpx
import requests
from pathlib import Path

import rich

from domain import DnsManager


class MailAccountManager:
    __docker_mail_server_config_dir__: str

    def __init__(self, config_dir: str):
        self.__docker_mail_server_config_dir__ = config_dir

    def list(self):
        """获取邮件账户列表"""
        client = docker.from_env()
        logs = client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                                     tty=False,
                                     stdin_open=False,
                                     volumes={
                                         self.__docker_mail_server_config_dir__: {'bind': f'/tmp/docker-mailserver',
                                                                                  'mode': 'rw'}},
                                     command=f"""setup email list""")
        return re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', logs)

    def add(self, name, pwd):
        """添加邮箱账户

        :param name: 用户名
        :param pwd: 密码
        """

        client = docker.from_env()
        client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                              tty=False,
                              stdin_open=False,
                              volumes={
                                  self.__docker_mail_server_config_dir__: {'bind': f'/tmp/docker-mailserver',
                                                                           'mode': 'rw'}},
                              command=f"""setup email add {name} {pwd}""")

    def update(self, name, npwd):
        """修改账户密码

        :param name: 用户名
        :param npwd: 新密码
        """

        client = docker.from_env()
        client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                              tty=False,
                              stdin_open=False,
                              volumes={
                                  self.__docker_mail_server_config_dir__: {'bind': f'/tmp/docker-mailserver',
                                                                           'mode': 'rw'}},
                              command=f"""setup email update {name} {npwd}""")

    def rem(self, name):
        """删除邮箱账户

        :param name:账户名
        """

        client = docker.from_env()
        client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                              tty=False,
                              stdin_open=False,
                              volumes={
                                  self.__docker_mail_server_config_dir__: {'bind': f'/tmp/docker-mailserver',
                                                                           'mode': 'rw'}},
                              command=f"""setup email del {name}""")


class SettingsManager:

    def __init__(self):
        with open('settings.json') as fs:
            self.json = json.load(fs)

    def get_component(self, component_name):
        """获取组件

        :param component_name: 组件名称
        """
        return next(x for x in self.json['components'] if x['name'] == component_name)

    def get_form(self, form_name):
        """获取表单

        :param form_name: 表单名称
        :return: 表单json
        """
        return self.json['forms'][form_name]


def dns_check(params):
    """检查dns记录是否正确

    :param params: 待检查的记录列表,[{name, ak,sk}, records...]
    """
    dns_manager = DnsManager.code_of(params[0]['name'])
    dns_manager.init(params[0]['ak'], params[0]['sk'])
    msg = ""
    # dns_manager.check_record()
    for record in params[1, len(params)]:
        if not dns_manager.check_record(record):
            msg += f"记录[{str(record)}{os.linesep}]不存在或不正确"
    return "所有记录已正确配置" if not msg else msg


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
