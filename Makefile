.PHONY: clean dev lint-python makemigrations migrate reset setup test test-python test-integration

COMPOSE_FILE := docker-compose.yml:docker-compose.dev.yml
export COMPOSE_FILE

EXEC_FLAGS ?=

dev:
	docker compose up --build

lint-python:
	docker compose exec $(EXEC_FLAGS) web ruff check .

makemigrations:
	docker compose exec $(EXEC_FLAGS) web python manage.py makemigrations

migrate:
	docker compose exec $(EXEC_FLAGS) web python manage.py migrate

setup:
	docker compose up -d --build
	docker compose exec $(EXEC_FLAGS) web python manage.py migrate
	docker compose exec $(EXEC_FLAGS) web python manage.py seed_development

clean:
	docker compose down -v

reset: clean setup
	docker compose down

test-python: lint-python
	docker compose exec $(EXEC_FLAGS) web pytest

test-integration:
	shellcheck tests/*.sh
	awk 'length > 88 { print FILENAME ":" NR ": " length " chars > 88"; print; err=1 } END { exit err }' tests/*.sh
	bats tests/*.bats

test: test-python test-integration
