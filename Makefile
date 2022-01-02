PHPLIST_DOWNLOAD_URL= http://103.231.174.66:1991
PHPLIST_VERSION = 3.6.6

all: build up

ui:
	docker build -t 'dongjak/mail-marketing-docker-setupui:latest' ./setupui && \
	docker run --name mail-marketing-docker-setupui -v $PWD:/app/main -p 5001:5001 -p 143:143 -p 465:465 -p 587:587 -p 993:993 dongjak/mail-marketing-docker-setupui:latest
build:
		docker-compose build \
		--build-arg VERSION=$(PHPLIST_VERSION) \
		--build-arg DOWNLOAD_URL=$(PHPLIST_DOWNLOAD_URL) \
		--no-cache
up:
	docker-compose  up -d