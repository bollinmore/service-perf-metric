IMAGE ?= spm-app:latest
PORT ?= 8000
NAME ?= spm

.PHONY: help build run stop logs compose-up compose-down shell

help:
	@echo "Targets: build, run, stop, logs, compose-up, compose-down, shell"

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm -it \
	  -p $(PORT):8000 \
	  -v "$$PWD/data:/app/data" \
	  -v "$$PWD/result:/app/result" \
	  -v "$$PWD/recycle:/app/recycle" \
	  --name $(NAME) $(IMAGE)

stop:
	-@docker stop $(NAME) >/dev/null 2>&1 || true

logs:
	docker logs -f $(NAME)

compose-up:
	docker compose up --build

compose-down:
	docker compose down

shell:
	docker run --rm -it \
	  -p $(PORT):8000 \
	  -v "$$PWD/data:/app/data" \
	  -v "$$PWD/result:/app/result" \
	  -v "$$PWD/recycle:/app/recycle" \
	  --entrypoint /bin/bash \
	  --name $(NAME)-shell $(IMAGE)

