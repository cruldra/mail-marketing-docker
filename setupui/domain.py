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
        elif (self.rdatatype.name == other['type'] and self.value == other['content'] and f"{self.name}.{self.host}" ==
              other['name']):
            return True
        return False

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

    def __init__(self, host, name, value, rdatatype: RdataType = RdataType.A, ttl: int = 0, id=""):
        self.__id__ = id
        self.__host__ = host
        self.__name__ = name
        self.__value__ = value
        self.__rdatatype__ = rdatatype
        self.__ttl__ = ttl


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
        record:dns记录
        unique:确保这条记录是唯一的
        """
        pass

    def deleteRecord(self, record_id: str):
        """删除记录
        record_id:记录id
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

    def addRecord(self, record: DnsRecord, unique: bool = False):
        if self.code == DnsManager.CLOUDFLARE.code:
            cf = CloudFlare.CloudFlare(email=self.ak, token=self.sk)
            zones = cf.zones.get(params={'name': record.host, 'per_page': 1})
            if len(zones) == 0:
                raise DnsException(f"请确认域名{record.host}成功交由{self.label}托管.")
            zone_id = zones[0]['id']
            dns_records = cf.zones.dns_records.get(zone_id)

            def predicate(dns_record):
                return record == dns_record

            if not any(predicate(elem) for elem in dns_records):
                res = cf.zones.dns_records.post(zone_id, data={
                    "name": record.name,
                    "type": record.rdatatype.name,
                    "content": record.value,
                })
            # for rs in list(filter(predicate, dns_records)):
            #     self.deleteRecord(rs['id'])

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
