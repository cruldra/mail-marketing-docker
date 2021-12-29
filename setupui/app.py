import json

from flask import Flask, render_template, request, url_for, redirect, Response
from flask.json import htmlsafe_dumps

from db import Database
from domain import DnsManager, get_dns_manager
from tools import my_ip, write_content_to_file, read_file_content, indices

app = Flask(__name__)


@app.route("/")
def index():
    fs = open('settings.json')
    settings = json.load(fs)
    fs.close()
    if not settings['forms']['domainAndIp']['ip']:
        settings['forms']['domainAndIp']['ip'] = my_ip()
    for com in settings['components']:
        com['logo'] = com['logo'] if com['logo'].startswith("/static") else url_for("static", filename=com['logo'])
    return render_template('index.html', settings=htmlsafe_dumps(settings),
                           dns_managers=htmlsafe_dumps(DnsManager.to_json_array()),
                           databases=htmlsafe_dumps(Database.to_json_array()))


@app.route("/install")
def install():
    return render_template('result.html')


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


if __name__ == '__main__':
    app.run(debug=True, port=5001, host="0.0.0.0")
