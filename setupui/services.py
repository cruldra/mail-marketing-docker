import json

import docker
from docker.errors import NotFound
from stringcase import alphanumcase, snakecase


def get_services():
    """获取服务列表"""

    def get_container_name(component_name):
        """获取组件的docker容器名称

        查找顺序:component_obj>sub_step>lower(component_name)
        """
        component = next(x for x in settings['components'] if x['name'] == component_name)
        default = snakecase(alphanumcase(component_name))
        if "container_name" in component:
            return component['container_name']
        elif "sub_step" in component:
            sub_step = settings['forms'][component['sub_step']['key']]
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
            "todo_list": component['todo_list'],
            "container_name": container_name,
            "status": get_status(container_name)
        }

    with open('settings.json') as fs:
        settings = json.load(fs)
    return list(map(component_mapper, settings['components']))
