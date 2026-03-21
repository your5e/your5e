.PHONY: clean dev lint-python makemigrations migrate reset scry setup test test-django test-sync-integration server-tests server-tests-down

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

scry:
	@ruff check scrying
	rm -f scrying/*.png
	python scrying/scry.py

server-tests:
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) up --build -d --wait
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T web-test python manage.py migrate
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T web-test python manage.py seed_development
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) exec -T db-test psql -U your5e postgres \
		-c "DROP DATABASE IF EXISTS your5e_seed" \
		-c "CREATE DATABASE your5e_seed WITH TEMPLATE your5e_test"

server-tests-down:
	COMPOSE_FILE=$(TEST_COMPOSE_FILE) docker compose -p $(TEST_COMPOSE_PROJECT) down -v

test-django: lint-python
	docker compose exec $(EXEC_FLAGS) web pytest

test-sync-integration:
	shellcheck tests/*.sh
	awk 'length > 88 { print FILENAME ":" FNR ": " length " chars > 88"; print; err=1 } END { exit err }' tests/*.sh
	bats tests/*.bats

test: test-django test-sync-integration
