from __future__ import annotations
import re
import this
from types import DynamicClassAttribute

import CloudFlare
import dns.resolver
from dns.rdatatype import RdataType
from enum import Enum


class DnsException(Exception):
    pass


class DnsRecord:
    __id__: str
    __host__: str
    __name__: str
    __value__: str
    __rdatatype__: RdataType
    __ttl__: int

    def __eq__(self, other):
        if self.id == other['id']:
            return True
        elif self.rdatatype.name == other['type'] and self.value == other['content']:
            if f"{self.name}.{self.host}" == other['name']:
                return True
            elif self.name == "@" and self.host == other['name']:
                return True
        return False

    @classmethod
    def from_dict(cls, dic: dict):
        return DnsRecord(host=dic['host'],
                         name=dic['name'],
                         value=dic['value'],
                         ttl=dic.get('ttl'),
                         rdatatype=RdataType(dic['type']))

    @DynamicClassAttribute
    def id(self):
        return self.__id__

    @DynamicClassAttribute
    def host(self):
        return self.__host__

    @DynamicClassAttribute
    def name(self):
        return self.__name__

    @DynamicClassAttribute
    def value(self):
        return self.__value__

    @DynamicClassAttribute
    def rdatatype(self):
        return self.__rdatatype__

    @DynamicClassAttribute
    def ttl(self):
        return self.__ttl__

    def to_json(self):
        return {
            "host": self.host,
            "name": self.name,
            "value": self.value,
            "type": self.rdatatype
        }

    def __init__(self, host, name, value, rdatatype: RdataType = RdataType.A, ttl: int = 0, id=""):
        self.__id__ = id
        self.__host__ = host
        self.__name__ = name
        self.__value__ = value
        self.__rdatatype__ = rdatatype
        self.__ttl__ = ttl

    def __str__(self) -> str:
        return f"{self.name}.{self.host}"

    def __repr__(self) -> str:
        return f"{self.name}.{self.host}"


class IDnsManager:
    __ak__: str
    __sk__: str

    @DynamicClassAttribute
    def ak(self):
        return self.__ak__

    @DynamicClassAttribute
    def sk(self):
        return self.__sk__

    def init(self, ak="", sk=""):
        self.__ak__ = ak
        self.__sk__ = sk

    def addRecord(self, record: DnsRecord, unique: bool = False):
        """添加记录

        :param  record: dns记录
        :param unique: 确保这条记录是唯一的
        """
        pass

    def list(self, host, **kwargs):
        """获取dns记录列表

        :param host: 域名
        """
        pass

    def deleteRecord(self, record_id: str):
        """删除记录
        record_id:记录id
        """
        pass

    def check_record(self, record: DnsRecord):
        """检查dns记录是否存在

        :param record: 要检查的dns记录
        """
        pass


class DnsManager(IDnsManager, Enum):
    CLOUDFLARE = ("cloudflare", "Cloudflare", "cloudflare.com")
    ALIYUN = ("aliyun", "阿里云", "hichina.com")
    NAMESILO = ("namesilo", "Namesilo", "namesilo.com")
    OTHER = ("other", "其它", "other")
    _code_: str
    _label_: str
    _nameserver_pattern_: str

    def __get_cf_zone_id__(self, host):
        cf = CloudFlare.CloudFlare(email=self.ak, token=self.sk)
        zones = cf.zones.get(params={'name': host, 'per_page': 1})
        if len(zones) == 0:
            raise DnsException(f"请确认域名{host}成功交由{self.label}托管.")
        return zones[0]['id']

    def list(self, host, **kwargs):
        def cloudflare():
            cf = CloudFlare.CloudFlare(email=self.ak, token=self.sk)
            return cf.zones.dns_records.get(self.__get_cf_zone_id__(host))

        handlers = {"cloudflare": cloudflare}
        if self.code not in handlers:
            raise DnsException(f"dns管理器{self.code}暂未提供支持")
        else:
            return handlers[self.code]()

    def addRecord(self, record: DnsRecord, unique: bool = False):
        def cloudflare():
            cf_zone_id = self.__get_cf_zone_id__(record.host)
            cf = CloudFlare.CloudFlare(email=self.ak, token=self.sk)
            if unique and self.check_record(record):
                return
            else:
                cf.zones.dns_records.post(cf_zone_id, data={
                    "name": record.name,
                    "type": record.rdatatype.name,
                    "content": record.value,
                    "ttl": record.ttl if record.ttl else 1,
                    'priority': 10
                })

        handlers = {"cloudflare": cloudflare}
        if self.code not in handlers:
            raise DnsException(f"dns管理器{self.code}暂未提供支持")
        else:
            return handlers[self.code]()

    def check_record(self, record: DnsRecord):
        def cloudflare():
            dns_records = self.list(record.host)
            return any(lambda it: it == record for _ in dns_records)

        handlers = {"cloudflare": cloudflare}
        if self.code not in handlers:
            raise DnsException(f"dns管理器{self.code}暂未提供支持")
        else:
            return handlers[self.code]()

    @classmethod
    def code_of(cls, code) -> DnsManager:
        return [item for item in DnsManager.values() if item.code == code][0]

    @classmethod
    def values(cls):
        _values = []
        for e in cls:
            _values.append(e)
        return _values

    @classmethod
    def to_json_array(cls):
        def to_json(el):
            return {"name": el.name, "value": el.value, "code": el.code, "label": el.label}

        return list(map(to_json, cls.values()))

    @DynamicClassAttribute
    def label(self):
        return self._label_

    @DynamicClassAttribute
    def code(self):
        return self._code_

    @DynamicClassAttribute
    def nameserver_pattern(self):
        return self._nameserver_pattern_

    def __init__(self, code, label, nameserver_pattern):
        self._code_ = code
        self._label_ = label
        self._nameserver_pattern_ = nameserver_pattern


def get_dns_manager(host) -> DnsManager:
    nameservers = "".join(get_name_server(host))

    def matcher(dns_manager):
        return re.search(dns_manager.nameserver_pattern, nameservers)

    return next(filter(matcher, DnsManager.values()))


def get_name_server(host):
    ans = dns.resolver.resolve(host, RdataType.NS)
    nameservers = []
    for rdata in ans:
        nameservers.append(str(rdata.target))
    nameservers.sort()
    return nameservers
