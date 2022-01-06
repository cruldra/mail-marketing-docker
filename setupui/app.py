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
from tools import my_ip, write_content_to_file, read_file_content, indices

app = Flask(__name__)
red = Redis('./redis.db')

settings_manager = tools.SettingsManager()


@app.route("/")
def index():
    # 如果请求参数中明确指定的需要激活的步骤
    if "active" in request.args:
        settings_manager.set_current_step(request.args['active'])

    # 自动获取当前服务器的ip
    myip = my_ip()
    domain_and_ip_form = settings_manager.get_form("domainAndIp")
    if not domain_and_ip_form['ip'] or domain_and_ip_form['ip'] != myip:
        domain_and_ip_form['ip'] = myip
    for com in settings_manager.json['components']:
        com['logo'] = com['logo'] if com['logo'].startswith("/static") else url_for("static", filename=com['logo'])
    return render_template('index.html', settings=htmlsafe_dumps(settings_manager.json),
                           dns_managers=htmlsafe_dumps(DnsManager.to_json_array()),
                           databases=htmlsafe_dumps(Database.to_json_array()))


@app.route("/services")
def services():
    """跳转到服务管理控制台"""
    return render_template('services.html', services=htmlsafe_dumps(settings_manager.get_services()))


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
    settings_manager.reload()
    settings_manager.active_previous_step()
    settings_manager.save()
    return redirect(url_for("index"))


@app.route("/next", methods=['POST'])
def next_step():
    settings_json = json.loads(request.form['json'])
    current_active_index = indices(settings_json['steps']['value'],
                                   lambda e: e['key'] == settings_json['steps']['active'])[0]
    if current_active_index + 1 < len(settings_json['steps']['value']):
        settings_json['steps']['active'] = settings_json['steps']['value'][current_active_index + 1]['key']
        settings_manager.save(settings_json)
        return redirect(url_for("index"))
    else:
        settings_manager.save(settings_json)
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
