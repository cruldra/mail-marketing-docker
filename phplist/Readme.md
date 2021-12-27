# 构建
```bash
docker build -t 'dongjak/phplist:3.6.6' --no-cache \
--build-arg VERSION="3.6.6" \
--build-arg DOWNLOAD_URL="http://103.231.174.66:1991" \
./
```

# 运行
```bash
docker run --name phplist -d -p 80:80  \
dongjak/phplist:3.6.6
```
