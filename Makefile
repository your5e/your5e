.PHONY: clean dev lint-python makemigrations migrate reset setup test test-python test-integration test-server test-server-down

COMPOSE_FILE := docker-compose.yml:docker-compose.dev.yml
export COMPOSE_FILE

TEST_COMPOSE_FILE := docker-compose.test.yml
TEST_COMPOSE_PROJECT := your5e-test

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
	docker compose exec $(EXEC_FLAGS) db pg_dump -U your5e your5e > tests/seed.sql

clean:
	docker compose down -v

reset: clean setup
	docker compose down

test-python: lint-python
	docker compose exec $(EXEC_FLAGS) web pytest

test-server:
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) up --build -d --wait
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T web-test python manage.py migrate
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T web-test python manage.py seed_development
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T db-test psql -U your5e postgres \
		-c "DROP DATABASE IF EXISTS your5e_seed" \
		-c "CREATE DATABASE your5e_seed WITH TEMPLATE your5e_test"

test-server-down:
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) down -v

test-integration:
	shellcheck tests/*.sh
	awk 'length > 88 { print FILENAME ":" FNR ": " length " chars > 88"; print; err=1 } END { exit err }' tests/*.sh
	bats tests/*.bats

test: test-python test-integration
