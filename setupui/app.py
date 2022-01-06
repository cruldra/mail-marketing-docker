import asyncio
import json
import _thread
import os
from inspect import getmembers, isfunction

from flask import Flask, render_template, request, url_for, redirect, Response
from flask.json import htmlsafe_dumps
from redislite import Redis
from termcolor import colored

import installer
import tools
from db import Database
from domain import DnsManager, get_dns_manager
from services import get_services
from tools import my_ip, write_content_to_file, read_file_content, indices

app = Flask(__name__)
red = Redis('./redis.db')


@app.route("/")
def index():
    with open('settings.json') as fs:
        settings = json.load(fs)
    if "active" in request.args:
        settings['steps']['active'] = request.args['active']
    myip = my_ip()
    if not settings['forms']['domainAndIp']['ip'] or settings['forms']['domainAndIp']['ip'] != myip:
        settings['forms']['domainAndIp']['ip'] = myip
    for com in settings['components']:
        com['logo'] = com['logo'] if com['logo'].startswith("/static") else url_for("static", filename=com['logo'])
    return render_template('index.html', settings=htmlsafe_dumps(settings),
                           dns_managers=htmlsafe_dumps(DnsManager.to_json_array()),
                           databases=htmlsafe_dumps(Database.to_json_array()))


@app.route("/services")
def services():
    """跳转到服务管理控制台"""
    return render_template('services.html', services=htmlsafe_dumps(get_services()))


@app.route("/install")
def install():
    """跳转到安装页面"""
    _thread.start_new_thread(installer.install, ())
    return render_template('install.html')


@app.route('/install_progress')
def install_progress():
    def format_sse(data, event=None) -> str:
        msg = f'data: {data.decode("utf-8") if isinstance(data, bytes) else str(data)}\n\n'
        if event is not None:
            msg = f'event: {event}\n{msg}'
        return msg

    def event_stream():
        pubsub = red.pubsub()
        pubsub.subscribe('installation_progress')
        for message in pubsub.listen():
            yield format_sse(message['data'], 'installation_progress')

    return Response(event_stream(),
                    mimetype="text/event-stream")


@app.route("/previous", methods=['POST'])
def previous_step():
    fs = open('settings.json')
    settings = json.load(fs)
    fs.close()
    current_active_index = indices(settings['steps']['value'],
                                   lambda e: e['key'] == settings['steps']['active'])[0]
    settings['steps']['active'] = settings['steps']['value'][current_active_index - 1]['key']
    write_content_to_file('settings.json', json.dumps(settings, indent=4, sort_keys=True))
    return redirect(url_for("index"))


@app.route("/next", methods=['POST'])
def next_step():
    settings_json = json.loads(request.form['json'])
    current_active_index = indices(settings_json['steps']['value'],
                                   lambda e: e['key'] == settings_json['steps']['active'])[0]
    if current_active_index + 1 < len(settings_json['steps']['value']):
        settings_json['steps']['active'] = settings_json['steps']['value'][current_active_index + 1]['key']
        write_content_to_file('settings.json', json.dumps(settings_json, indent=4, sort_keys=True))
        return redirect(url_for("index"))
    else:
        write_content_to_file('settings.json', json.dumps(settings_json, indent=4, sort_keys=True))
        return redirect(url_for("install"))


@app.route("/dns/detect")
def detect_dns_manager():
    try:
        return get_dns_manager(request.args.get("host")).code, 200
    except Exception as e:
        return DnsManager.OTHER.code, 200


@app.route("/todo", methods=['POST'])
def todo():
    try:
        task = request.json['task']
        component_name = request.json['component_name']
        if task['redirect']:
            res = {
                "code": 0,
                "data": url_for(task['endpoint'], **task['parameters'])
            }
        else:
            func = next(fun for fun in getmembers(tools, isfunction) if fun[0] == task['endpoint'])[1]
            res = {
                "code": 0,
                "data": func(task['parameters'])
            }

        # 如果是一次性任务,执行完成后从组件的todo_list中移除
        with open('settings.json') as fs:
            settings = json.load(fs)
        component = next(x for x in settings['components'] if x['name'] == component_name)
        if task['persistence'] == "once":
            component['todo_list'].pop([task.name], None)
        write_content_to_file('settings.json', json.dumps(settings, indent=4, sort_keys=True))
        return res

    except Exception as e:
        return {
            "code": 0,
            "msg": str(e)
        }


@app.route("/mail-server/accounts")
def manage_mail_accounts():
    pass


@app.route("/mail-server/accounts/pwd/update", methods=['POST'])
def update_mail_account_pwd():
    """修改邮箱账户密码"""
    try:
        settings_manager = tools.SettingsManager()
        set_mail_server_form = settings_manager.get_form('setMailServer')
        mail_server_config_dir = os.path.abspath(f"{__file__}/../../{set_mail_server_form['data_dir']}/config")
        mail_account_manager = tools.MailAccountManager(mail_server_config_dir)
        mail_account_manager.update(request.args['name'], request.args['npwd'])
        return {
            "code": 0
        }
    except Exception as e:
        return {
            "code": 1,
            "msg": str(e)
        }


if __name__ == '__main__':
    app.run(debug=True, port=5001, host="0.0.0.0")
