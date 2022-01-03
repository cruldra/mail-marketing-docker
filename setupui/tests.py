import json
import os
import re
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import html as html
from urllib.request import urlretrieve

import docker
import pydnsbl
import requests
import yaml
from dns.rdatatype import RdataType
from docker import APIClient
from dotenv import load_dotenv, set_key
from redislite import Redis
from termcolor import colored
from bs4 import BeautifulSoup
from domain import get_name_server, DnsManager, get_dns_manager, DnsRecord


class CallShellCommandTests(unittest.TestCase):
    def test_by_os(self):
        print(os.system("""
        cat  /Users/liuye/fsdownload/mail.txt 
        """))

    def test_cat_mail_txt(self):
        pattern = re.compile(r'\"(.*)\"')
        res = pattern.findall(Path("/Users/liuye/fsdownload/mail.txt").read_text())

        print("".join(res))

class EnvFileTests(unittest.TestCase):
    def test_load_env(self):
        env_file_path = os.path.abspath(f"{__file__}/../../ms.env")
        load_dotenv(env_file_path)
        set_key(env_file_path, "TZ", "asdfadfa")
        print(os.getenv('TZ'))


class FileDownloadTests(unittest.TestCase):
    def test_download_file(self):
        man_script_path = os.path.abspath(__file__ + "/../../msman.sh")
        urlretrieve("https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh",
                    man_script_path)
        st = os.stat(man_script_path)
        os.chmod(man_script_path, st.st_mode | stat.S_IEXEC)
        os.symlink(man_script_path, "/usr/local/bin/msman")


class CertInstallTests(unittest.TestCase):
    def test_print_cmd(self):
        domain = "hasaiki.xyz"
        email = "cruldra@cruldra.cn"
        cf_token = "ozTikFmlS9bxLmnJqLc80uCLCeBAQvcXOJ8mTVeW"
        print(f"""echo "dns_cloudflare_api_token = {cf_token}" >> /cloudflare.ini certonly  --noninteractive \
                              --agree-tos -m {email} --preferred-challenges dns --expand  --dns-cloudflare  --dns-cloudflare-credentials /cloudflare.ini  \
                              -d *.{domain}  --server https://acme-v02.api.letsencrypt.org/directory""")

    def test_docker_low_level_api(self):
        client = APIClient(base_url='unix://var/run/docker.sock')
        client.logs()
        print(client)

    def test_cloudflare(self):
        domain = "9l2z.xyz"
        email = "cruldra@cruldra.cn"
        cf_token = "ozTikFmlS9bxLmnJqLc80uCLCeBAQvcXOJ8mTVeW"

        cloudflare_ini = Path(os.path.abspath(__file__ + "/../../config/cloudflare.ini"))
        cloudflare_ini.write_text(f"dns_cloudflare_api_token = {cf_token}")
        client = docker.from_env()
        container = client.containers.run(image='certbot/dns-cloudflare', detach=True, auto_remove=False, tty=True,
                                          stdin_open=True,
                                          name="certbot", volumes={
                os.path.abspath(__file__ + "/../../config/certs"): {'bind': f'/etc/letsencrypt/archive',
                                                                    'mode': 'rw'},
                cloudflare_ini: {'bind': '/cloudflare.ini', 'mode': 'ro'}},
                                          command=f"""certonly  --noninteractive \
                                                  --agree-tos -m {email} --preferred-challenges dns --expand  --dns-cloudflare  --dns-cloudflare-credentials /cloudflare.ini  \
                                                  -d *.{domain}  --server https://acme-v02.api.letsencrypt.org/directory""")
        print(container)
        # client = APIClient(base_url='unix://var/run/docker.sock')
        # generator = client.logs("certbot")
        # while True:
        #     output = generator.__next__
        #     print(output)
        # try:
        #     output = output.strip('\r\n')
        #     json_output = json.loads(output)
        #     if 'stream' in json_output:
        #         click.echo(json_output['stream'].strip('\n'))
        # except StopIteration:
        #     click.echo("Docker image build complete.")
        #     break
        # except ValueError:
        #     click.echo("Error parsing output from docker image build: %s" % output)
        # for log in container.logs():
        #     print(log)
        # with tempfile.NamedTemporaryFile(suffix='.ini', prefix="cloudflare", mode="w") as tf:
        #     tf.write("dns_cloudflare_api_token = {cf_token}")
        #     tf.flush()

    def test_run_docker_container(self):
        client = docker.from_env()
        container = client.containers.run(image='dongjak/layui-chinese-doc:latest', detach=False,
                                          name="layui-chinese-doc11")
        print(container)


class InstallerTests(unittest.TestCase):

    def test_ip_reputation(self):
        # url = "https://check.spamhaus.org/not_listed/?searchterm=234234124"
        #
        # payload = {}
        # headers = {
        #     'authority': 'check.spamhaus.org',
        #     'cache-control': 'max-age=0',
        #     'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        #     'sec-ch-ua-mobile': '?0',
        #     'sec-ch-ua-platform': '"macOS"',
        #     'dnt': '1',
        #     'upgrade-insecure-requests': '1',
        #     'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        #     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        #     'sec-fetch-site': 'same-origin',
        #     'sec-fetch-mode': 'navigate',
        #     'sec-fetch-user': '?1',
        #     'sec-fetch-dest': 'document',
        #     'referer': 'https://check.spamhaus.org/?__cf_chl_jschl_tk__=HKPUvZk3PYSeyi.hqRqvP4wzGsLd_CHw6hhaPQ03BFE-1640871808-0-gaNycGzNCb0',
        #     'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        #     'cookie': 'cb-enabled=enabled; _hjSessionUser_1643020=eyJpZCI6IjA2MjRkMGYyLTIxZmQtNTlmYy05YWJhLWEyZGE5ODA5MzMzZSIsImNyZWF0ZWQiOjE2NDA1ODcwMzMxMTcsImV4aXN0aW5nIjp0cnVlfQ==; cf_clearance=DMvxc0heQN6tfdFwwIpxmf4OoXzcOEjAkLr20prveQg-1640871811-0-150; PHPSESSID=qe7ceuo55a34jnbcq5ao49vmgm; _hjSession_1643020=eyJpZCI6IjFlOGQzODcyLTZjYWEtNDY0My1iZDJlLTVlMDgzZjk3ZDQ1NyIsImNyZWF0ZWQiOjE2NDA4NzE4MTQ4ODR9'
        # }
        # response = requests.request("GET", url, headers=headers, data=payload)
        # # print(response.text)
        # soup = BeautifulSoup(response.text)
        # print(soup.select(".page-header>h2")[0].text)
        ip_checker = pydnsbl.DNSBLIpChecker()
        # self.assertTrue(ip_checker.check('120.242.217.223').blacklisted) # 本机
        # print(ip_checker.check('194.5.78.236')) # 西伯利亚测试机
        # print(ip_checker.check('103.231.174.66'))# api
        print(ip_checker.check('106.13.64.61'))
        # self.assertFalse(ip_checker.check('194.5.78.236').blacklisted)


class YieldExpTestCase(unittest.TestCase):
    def testYield(self):
        def foo():
            print("starting...")
            while True:
                res = yield 4
                print("res:", res)

        g = foo()
        print(next(g))
        print("*" * 20)
        print(next(g))


class DomainTestCase(unittest.TestCase):
    def test_cloudflare_add_record(self):
        """测试使用cloudflare api添加解析记录"""
        domain = "9l2z.xyz"
        manager = get_dns_manager(domain)
        manager.init(sk="ozTikFmlS9bxLmnJqLc80uCLCeBAQvcXOJ8mTVeW")
        manager.addRecord(record=DnsRecord(host=domain, name='@', rdatatype=RdataType.MX,
                                           value=f"mail.{domain}"), unique=True)
        # manager.addRecord(
        #     record=DnsRecord(host=domain, name="test", value="120.12.13.14", rdatatype=RdataType.A))

    def test_get_name_server(self):
        nameservers = get_name_server("civetcat.net")
        self.assertEqual(nameservers[1], "porter.ns.cloudflare.com.")  # add assertion here
        self.assertEqual(get_dns_manager("civetcat.net"), DnsManager.CLOUDFLARE)

    def test_dns_manager_enum(self):
        # for e in DnsManager:
        #     print(e)
        values = DnsManager.to_json_array()
        print(json.dumps(values))
        self.assertEqual(DnsManager.NAMESILO.label, "Namesilo")

    def test_get_nameserver(self):
        process = subprocess.Popen(["dig", "+short", "ns", "civetcat.net"], stdout=subprocess.PIPE,
                                   universal_newlines=True)
        output = process.communicate()

        ip_arr = []
        for data in output:
            if 'Address' in data:
                ip_arr.append(data.replace('Address: ', ''))
        ip_arr.pop(0)

        print
        ip_arr
        self.assertEqual(1, 1)  # add assertion here


class RedisLiteTestCase(unittest.TestCase):
    def test_chinese_support(self):
        redis_connection = Redis('./redis.db')
        s = u"我草"
        s.encode('UTF-8')
        redis_connection.set("a", s)
        print(redis_connection.get("a").decode("UTF-8"))

    def test_redis_lite_pu_sub(self):
        redis_connection = Redis('./redis.db')
        redis_connection.publish('chat', '#########')
        redis_connection.publish('chat', '1')
        redis_connection.publish('chat', '2')
        redis_connection.publish('chat', '3')
        pubsub = redis_connection.pubsub()
        pubsub.subscribe('chat')
        for message in pubsub.listen():
            print(message)
            yield 'data: %s\n\n' % message['data']


class ConsoleColorTestCase(unittest.TestCase):
    def test_print_color(self):
        print(
            f"如果你正在{colored('Docker', 'green')}中运行{colored('setupui', 'green')},请使用链接{colored('http://your_host:5001', 'green')}")


class YamlTestCase(unittest.TestCase):
    def test_load_yaml(self):
        p = Path("/Users/liuye/DockerProjects/mail-marketing-docker/docker-compose.yml")
        doc = yaml.safe_load(p.read_text())
        print(yaml.dump(doc))


if __name__ == '__main__':
    unittest.main()
