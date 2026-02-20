COMPOSE_FILE := docker-compose.yml:docker-compose.dev.yml
export COMPOSE_FILE

.PHONY: dev lint migrate reset test

dev:
	docker compose up --build

lint:
	docker compose exec web ruff check .

migrate:
	docker compose run --rm web python manage.py migrate

reset:
	docker compose down -v
	docker compose build web
	docker compose run --rm web python manage.py migrate
	docker compose run --rm web python manage.py seed_development

test: lint
	docker compose exec web pytest
