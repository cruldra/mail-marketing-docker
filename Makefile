PHPLIST_DOWNLOAD_URL= http://103.231.174.66:1991
PHPLIST_VERSION = 3.6.6
PROJECT_DIR = $(shell pwd)
SETUPUI_DIR = $(PROJECT_DIR)/setupui
all: build up
test:
	echo $(PROJECT_DIR) && echo $(SETUPUI_DIR)
ui:
	docker run  --rm --name create_venv -v $(SETUPUI_DIR):/app continuumio/miniconda3 conda create  -p /app/.venv python=3.9 && \
    cd $(SETUPUI_DIR) && .venv/bin/python -m pip install --no-cache-dir -r requirements.txt  && \
    cd $(SETUPUI_DIR) && (mkdir .logs || true) && (touch .logs/setupui.log || true) && \
    cd $(SETUPUI_DIR) && .venv/bin/python app.py
build:
		docker-compose build \
		--build-arg VERSION=$(PHPLIST_VERSION) \
		--build-arg DOWNLOAD_URL=$(PHPLIST_DOWNLOAD_URL) \
		--no-cache
up:
	docker-compose  up -d