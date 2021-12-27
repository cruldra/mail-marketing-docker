PHPLIST_DOWNLOAD_URL= http://103.231.174.66:1991
PHPLIST_VERSION = 3.6.6

all: build up

build:
		docker-compose build \
		--build-arg VERSION=$(PHPLIST_VERSION) \
		--build-arg DOWNLOAD_URL=$(PHPLIST_DOWNLOAD_URL) \
		--no-cache
up:
	docker-compose  up -d