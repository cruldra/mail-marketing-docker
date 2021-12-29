import json
import unittest
import subprocess
from pathlib import Path

import CloudFlare
import yaml
from dns.rdatatype import RdataType

from domain import get_name_server, DnsManager, get_dns_manager, DnsRecord


class DomainTestCase(unittest.TestCase):
    def test_cloudflare_add_record(self):
        """测试使用cloudflare api添加解析记录"""
        manager = get_dns_manager("civetcat.net")
        manager.init(sk="ozTikFmlS9bxLmnJqLc80uCLCeBAQvcXOJ8mTVeW")
        manager.addRecord(
            record=DnsRecord(host="civetcat.net", name="test", value="120.12.13.14", rdatatype=RdataType.A))

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
        process = subprocess.Popen(["dig", "+short", "ns", "civetcat.net"], stdout=subprocess.PIPE)
        output = process.communicate()[0].split('\n')

        ip_arr = []
        for data in output:
            if 'Address' in data:
                ip_arr.append(data.replace('Address: ', ''))
        ip_arr.pop(0)

        print
        ip_arr
        self.assertEqual(1, 1)  # add assertion here


class YamlTestCase(unittest.TestCase):
    def test_load_yaml(self):
        p = Path("/Users/liuye/DockerProjects/mail-marketing-docker/docker-compose.yml")
        doc = yaml.safe_load(p.read_text())
        print(yaml.dump(doc))


if __name__ == '__main__':
    unittest.main()
