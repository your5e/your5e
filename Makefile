COMPOSE_FILE := docker-compose.yml:docker-compose.dev.yml
export COMPOSE_FILE

.PHONY: dev lint-python makemigrations migrate reset test test-python test-integration

dev:
	docker compose up --build

lint-python:
	docker compose exec web ruff check .

makemigrations:
	docker compose exec web python manage.py makemigrations

migrate:
	docker compose run --rm web python manage.py migrate

reset:
	docker compose down -v
	docker compose build web
	docker compose run --rm web python manage.py migrate
	docker compose run --rm web python manage.py seed_development

test-python: lint-python
	docker compose exec web pytest

test-integration:
	bats tests/*.bats

test: test-python test-integration
