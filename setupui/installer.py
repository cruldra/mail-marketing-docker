import json
import logging
import os
import re
import ssl
import stat
from pathlib import Path

import docker
import pydnsbl
import yaml
from urllib.request import urlretrieve
from dns.rdatatype import RdataType
from docker.errors import ContainerError
from dotenv import load_dotenv, set_key
from redislite import Redis

from domain import DnsManager, DnsRecord
from localhost_port import LocalHostPort
from log import SSEHandler, formatter, logger
from tools import indices, download_file

# region 日志设置
red = Redis('./redis.db')
sse_handler = SSEHandler(red, "installation_progress")
sse_handler.setFormatter(formatter)
logger.addHandler(sse_handler)


# endregion 日志设置


def __init_docker_compose_file__():
    p = Path(os.path.abspath(__file__ + "/../../docker-compose.yml"))
    if not p.exists():
        p.write_text(yaml.dump({"version": "3.7", "networks": {"network": None}}))
    return yaml.safe_load(p.read_text())


def install():
    docker_compose_doc = __init_docker_compose_file__()
    fs = open('settings.json')
    settings = json.load(fs)
    fs.close()

    def component_setup(name, installer, service_name):
        """根据settings.json中的设定添加或删除组件

        name:组件名称
        installer:安装器
        """
        component = \
            [item for item in settings['components'] if item.get('name') == name][0]
        component_checked = component['checked']
        if component_checked:
            installer(settings, docker_compose_doc)
        else:
            docker_compose_doc['services'].pop(service_name, None)

    component_setup("Docker Mail Server", __install_mail_server__, "mailserver")
    component_setup("phpList", __install_phplist__, "phplist")
    component_setup("Database", __install_db__, "db")
    Path(os.path.abspath(__file__ + "/../../docker-compose.yml")).write_text(yaml.dump(docker_compose_doc))


def __install_phplist__(settings, docker_compose_doc):
    pass


def __install_db__(settings, docker_compose_doc):
    pass


def __install_mail_server__(settings, docker_compose_doc):
    """安装docker mail server"""

    domain_and_ip_form = settings['forms']['domainAndIp']
    dns_manager = DnsManager.code_of(domain_and_ip_form['dnsManager'])
    dns_manager.init(ak=domain_and_ip_form['ak'], sk=domain_and_ip_form['sk'])
    domain = domain_and_ip_form['domain']
    ip = domain_and_ip_form['ip']

    set_mail_server_form = settings['forms']['setMailServer']
    docker_container_name = set_mail_server_form['container_name']
    docker_container_dns = set_mail_server_form['dns']
    docker_data_dir = set_mail_server_form['data_dir']

    def pre_check():
        """预检
        :25端口是否开通
        :ip是否包含在black list
        """
        port = LocalHostPort(25)
        port.test()
        if port.already_in_use:
            logger.error("25端口当前被其它程序占用")
        if not port.allow_incoming:
            logger.error("25端口不可用,请检查防火墙配置")
        if not port.allow_outgoing:
            logger.error("25端口不可用,请确认你的服务器供应商没有禁用25端口")
        ip_checker = pydnsbl.DNSBLIpChecker()
        if ip_checker.check(ip).blacklisted:
            logger.warning("通过ip信用检查,你的ip可能无法发送邮件")

    pre_check()

    # region 添加dns记录
    logger.info("添加dns记录")
    dns_manager.addRecord(record=DnsRecord(host=domain, name='mail', rdatatype=RdataType.A,
                                           value=ip), unique=True)
    dns_manager.addRecord(record=DnsRecord(host=domain, name='_dmarc', rdatatype=RdataType.TXT,
                                           value=f"v=DMARC1; p=quarantine; rua=mailto:dmarc.report@{domain}; ruf=mailto:dmarc.report@{domain}; fo=0; adkim=r; aspf=r; pct=100; rf=afrf; ri=86400; sp=quarantine"),
                          unique=True)
    dns_manager.addRecord(record=DnsRecord(host=domain, name='@', rdatatype=RdataType.TXT,
                                           value="v=spf1 mx ~all"), unique=True)
    dns_manager.addRecord(record=DnsRecord(host=domain, name='@', rdatatype=RdataType.MX,
                                           value=f"mail.{domain}"), unique=True)
    # endregion

    # region 申请证书
    logger.info("正在申请证书")
    try:
        cloudflare_ini = Path(os.path.abspath(__file__ + "/../../config/cloudflare.ini"))
        cloudflare_ini.write_text(f"dns_cloudflare_api_token = {domain_and_ip_form['sk']}")
        client = docker.from_env()
        logs = client.containers.run(image='certbot/dns-cloudflare', detach=False, auto_remove=True, tty=True,
                                     stdin_open=True,
                                     name="certbot", volumes={
                os.path.abspath(__file__ + "/../../config/certs"): {'bind': f'/etc/letsencrypt/archive',
                                                                    'mode': 'rw'},
                cloudflare_ini: {'bind': '/cloudflare.ini', 'mode': 'ro'}},
                                     command=f"""certonly  --noninteractive \
                                                          --agree-tos -m root@{domain} --preferred-challenges dns --expand  --dns-cloudflare  --dns-cloudflare-credentials /cloudflare.ini  \
                                                          -d *.{domain}  --server https://acme-v02.api.letsencrypt.org/directory""")
        logger.info(logs)
    except ContainerError as e:
        pass
    finally:
        if Path(os.path.abspath(f"{__file__}/../../config/certs/{domain}/privkey1.pem")).exists():
            logger.info("证书申请成功")
        else:
            logger.error("证书申请失败")
    # endregion

    # region 下载辅助脚本及添加执行权限
    logger.info("下载辅助脚本")
    man_script_path = os.path.abspath(__file__ + "/../../msman.sh")
    download_file("https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh",man_script_path)
    st = os.stat(man_script_path)
    os.chmod(man_script_path, st.st_mode | stat.S_IEXEC)
    os.symlink(man_script_path, "/usr/local/bin/msman")
    logger.info(f"辅助脚本已下载,使用 msman help 获取更多帮助信息.")
    # endregion

    # region 修改mailserver.env
    logger.info("配置环境变量")
    env_file_path = os.path.abspath(f"{__file__}/../../ms.env")
    load_dotenv(env_file_path)
    set_key(env_file_path, "TZ", "Asia/Shanghai")
    set_key(env_file_path, "POSTMASTER_ADDRESS", f"root@{domain}")
    set_key(env_file_path, "PERMIT_DOCKER", "network")
    set_key(env_file_path, "SSL_TYPE", "manual")
    set_key(env_file_path, "SSL_CERT_PATH", "/tmp/ssl/fullchain1.pem")
    set_key(env_file_path, "SSL_KEY_PATH", "/tmp/ssl/privkey1.pem")
    logger.info("环境变量配置完成")
    # endregion

    # region 创建管理员账户
    logger.info("创建管理员账户")
    client = docker.from_env()
    logs = client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                                 tty=False,
                                 stdin_open=False, volumes={
            os.path.abspath(__file__ + "/../../.mailserver-data/config"): {'bind': f'/tmp/docker-mailserver',
                                                                           'mode': 'rw'}},
                                 command=f"""setup email add roo@{domain} 123456""")
    logger.info(logs)
    # endregion

    # region 配置dkim
    logger.info("配置dkim")
    logs = client.containers.run(image='docker.io/mailserver/docker-mailserver', detach=False, auto_remove=True,
                                 tty=False,
                                 stdin_open=False, volumes={
            os.path.abspath(__file__ + "/../../.mailserver-data/config"): {'bind': f'/tmp/docker-mailserver',
                                                                           'mode': 'rw'}},
                                 command=f"""setup config dkim keysize 512""")
    pattern = re.compile(r'\"(.*)\"')
    key_file_path = Path(os.path.abspath(f"{__file__}/../../.mailserver-data/config/opendkim/keys/{domain}/mail.txt"))
    res = pattern.findall(key_file_path.read_text())
    dns_manager.addRecord(record=DnsRecord(host=domain, name='mail._domainkey', rdatatype=RdataType.TXT,
                                           value=f'{"".join(res)}'), unique=True)
    logger.info(logs)
    # endregion

    # 将docker mail server服务描述写入docker-compose.yml
    docker_compose_doc['services']['mailserver'] = {
        "image": "docker.io/mailserver/docker-mailserver:latest",
        "container_name": docker_container_name if docker_container_name else "mailserver",
        "dns": docker_container_dns if docker_container_dns else "1.1.1.1",
        "hostname": "mail",
        "domainname": domain,
        "env_file": "mailserver.env",
        "ports": ["25:25", "143:143", "465:465", "587:587", "993:993"],
        "volumes": [f"{docker_data_dir}/mail-data/:/var/mail/",
                    f"{docker_data_dir}/mail-state/:/var/mail-state/",
                    f"{docker_data_dir}/mail-logs/:/var/log/mail/",
                    f"{docker_data_dir}/config/:/tmp/docker-mailserver/",
                    f"/etc/localtime:/etc/localtime:ro",
                    f"./config/certs/{domain}/:/tmp/ssl/:ro"],
        "restart": "always",
        "stop_grace_period": "1m",
        "cap_add": ["NET_ADMIN", "SYS_PTRACE"]
    }
    logger.info("Docker Mail Server安装完成")


if __name__ == '__main__':
    install()
