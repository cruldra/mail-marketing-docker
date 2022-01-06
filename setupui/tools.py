import json
import os
import re
import socket

import docker
import httpx
import requests
from pathlib import Path

import rich
from docker.errors import NotFound
from stringcase import snakecase, alphanumcase

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

    def __init__(self, file='settings.json'):
        self.json = None
        self.file = file
        self.reload()

    def reload(self):
        """重新加载设置文档"""
        with open(self.file) as fs:
            self.json = json.load(fs)

    def component_task_completed(self, component_name, task):
        """指示组件的某个任务已完成

        如果任务是一次性的,则从组件任务中移除

        :param component_name: 组件名称
        :param task: 任务
        """
        if task['persistence'] == "once":
            self.get_component(component_name)['todo_list'].pop(task.name, None)

    def get_active_step_index(self):
        """获取当前激活的步骤的索引"""

        return indices(self.json['steps']['value'],
                       lambda e: e['key'] == self.json['steps']['active'])[0]

    def active_previous_step(self):
        """激活上一个步骤"""
        self.json['steps']['active'] = self.json['steps']['value'][self.get_active_step_index() - 1]['key']

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

    def get_current_step(self):
        """获取当前正在进行的步骤"""
        return self.json['steps']['active']

    def set_current_step(self, step):
        """设置当前步骤"""
        self.json['steps']['active'] = step

    def save(self, settings=None):
        """保存设置

        :param settings: 如果提供了此参数,则覆盖
        """
        write_content_to_file(self.file, json.dumps(self.json if not settings else settings, indent=4, sort_keys=True))

    def add_task_to_component(self, component_name, task):
        """添加todo任务到组件

        在所有任务全部添加完毕后,记得调用save()保存

        :param component_name: 组件名称
        :param task: 任务
        :return:
        """
        component = self.get_component(component_name)
        if "todo_list" not in component:
            component['todo_list'] = {}

        # 名字重复且参数是一个列表的情况下,直接追加参数而不是新建任务
        if task['name'] in component['todo_list'] and isinstance(task['parameters'], list):
            component['todo_list'][task['name']]['parameters'] += task['parameters']
        else:
            component['todo_list'][task['name']] = task

    def get_services(self):
        """获取服务列表"""

        def get_container_name(component_name):
            """获取组件的docker容器名称

            查找顺序:component_obj>sub_step>lower(component_name)
            """
            component = self.get_component(component_name)
            default = snakecase(alphanumcase(component_name))
            if "container_name" in component:
                return component['container_name']
            elif "sub_step" in component:
                sub_step = self.json['forms'][component['sub_step']['key']]
                if "container_name" in sub_step:
                    return sub_step['container_name']
                else:
                    return default
            else:
                return default

        def get_status(container_name):
            client = docker.from_env()
            installed = None
            try:
                installed = client.containers.get(container_name) is not None
            except NotFound as e:
                installed = False
            running = False if not installed else client.containers.get(container_name).status == "running"
            label = None
            if not installed and not running:
                label = "未安装"
            elif installed and not running:
                label = "未启动"
            elif installed and running:
                label = "运行中"
            return {
                "installed": installed,
                "running": running,
                "label": label
            }

        def component_mapper(component):
            component_name = component['name']
            container_name = get_container_name(component_name)
            return {
                "name": component_name,
                "todo_list": component.get('todo_list', {}),
                "container_name": container_name,
                "status": get_status(container_name)
            }

        return list(map(component_mapper, self.json['components']))


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
