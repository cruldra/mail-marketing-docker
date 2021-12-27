FROM php:7.4.27-apache-bullseye
MAINTAINER dongjak <cruldra@gmail.com>
ENV OS_LOCALE="zh_CN.UTF-8"
RUN apt-get update && \
    apt-get install -y locales && \
    echo "zh_CN.UTF-8 UTF-8" |tee -a /etc/locale.gen && \
    locale-gen ${OS_LOCALE} && \
    mkdir -p /app
ENV LANG=${OS_LOCALE} \
    LANGUAGE=${OS_LOCALE} \
    LC_ALL=${OS_LOCALE} \
    DEBIAN_FRONTEND=noninteractive
# phplist程序包下载链接
ARG DOWNLOAD_URL
# phplist程序版本
ARG VERSION
RUN buildDeps=" \
        default-libmysqlclient-dev \
        libbz2-dev \
        libmemcached-dev \
        libsasl2-dev \
    " \
    runtimeDeps=" \
        curl \
        git \
        libfreetype6-dev \
        libicu-dev \
        libjpeg-dev \
        libldap2-dev \
        libmcrypt-dev \
        libmemcachedutil2 \
        libpng-dev \
        libpq-dev \
        libxml2-dev \
        openssh-client \
        rsync \
        wget \
        unzip \
        libc-client-dev \
        libkrb5-dev \
    " \
    # 安装依赖 \
    && apt-get update &&  apt-get install -y --no-install-recommends  $buildDeps $runtimeDeps \
    && curl  -o /app/phplist-${VERSION}.zip ${DOWNLOAD_URL}/phplist-${VERSION}.zip \
    && cd /app && unzip phplist-${VERSION}.zip \
    && mv /app/phplist-${VERSION}/public_html/lists/* /var/www/html \
    && echo "<?php" >> /var/www/html/phpinfo.php \
    && echo "phpinfo();" >> /var/www/html/phpinfo.php \
    && rm -f /var/www/html/index.html \
    && chmod -R 777 /var/www/html \
    && echo 'install php extensions' \
    # 安装需要的php扩展 \
    && docker-php-ext-configure imap --with-kerberos --with-imap-ssl  \
    && docker-php-ext-install imap gd mysqli \
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -r /var/lib/apt/lists/* \
    && a2enmod rewrite \
    # 刷新Lets Encrypt证书
    && sed -i 's#mozilla\/DST_Root_CA_X3.crt#!mozilla\/DST_Root_CA_X3.crt#g' /etc/ca-certificates.conf \
    && update-ca-certificates --fresh
