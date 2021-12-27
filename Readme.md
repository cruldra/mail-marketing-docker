# 邮件营销服务Docker镜像
## 使用到的docker镜像
### [Docker Mailserver](https://github.com/docker-mailserver/docker-mailserver)
一个功能齐全但简单的邮件服务器,包括SMTP、IMAP、LDAP、反垃圾邮件、防病毒等

### [phplist](https://www.phplist.org/)
开源免费的邮件营销软件

### [mysql](https://hub.docker.com/layers/mysql/library/mysql/5.5.62/images/sha256-d404d78aa797c87c255e5ae2beb5d8d0e4d095f930b1f20dc208eaa957477b74)
mysql数据库,[phplist](#phplist)会用到


## 构建及启动
```bash
# 开发环境构建
mkdir -p /app && \
cd /app && \
git clone https://cruldra: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@github.com/cruldra/wwmh-docker.git && \
cd /app/wwmh-docker/alipay && \
source dev.sh && \
docker-compose build  --build-arg VERSION="1.0.0"   --no-cache 

# 生产环境构建
echo 1 > /var/log/alipay.log && \
rm -rf /app/wwmh-docker || true && \
mkdir -p /app && \
cd /app && \
git clone https://cruldra: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@github.com/cruldra/wwmh-docker.git && \
cd /app/wwmh-docker/alipay && \
source prod.sh && \
docker-compose build  --build-arg VERSION="1.0.0" --no-cache 

# 启动/重启
cd /app/wwmh-docker/alipay && \
source prod.sh && \
docker-compose  up -d
