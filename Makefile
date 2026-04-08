.PHONY: clean setup reset dev
.PHONY: server-tests server-tests-down test lint-django test-django test-sync-integration
.PHONY: css makemigrations migrate scry shell
.PHONY: terraform-plan terraform-apply ansible-bootstrap ansible-os ansible-app
.PHONY: build deploy update-notebooks

COMPOSE_FILE := docker-compose.yml:docker-compose.dev.yml
export COMPOSE_FILE

TEST_COMPOSE_FILE := docker-compose.test.yml
TEST_COMPOSE_PROJECT := your5e-test

EXEC_FLAGS ?=

dev:
	docker compose up --build

lint-django:
	docker compose exec $(EXEC_FLAGS) web ruff check .
	awk -v max=120 -f tests/check-line-length.awk templates/**/*.html static/css/source/**/*.scss

makemigrations:
	docker compose exec $(EXEC_FLAGS) web python manage.py makemigrations

migrate:
	docker compose exec $(EXEC_FLAGS) web python manage.py migrate

shell:
	docker compose exec $(EXEC_FLAGS) web python manage.py shell

setup:
	docker compose up -d --build
	docker compose exec $(EXEC_FLAGS) web python manage.py migrate
	docker compose exec $(EXEC_FLAGS) web python manage.py seed_development
	docker compose exec $(EXEC_FLAGS) web python manage.py import_notebook --all
	docker compose exec $(EXEC_FLAGS) db pg_dump -U your5e your5e > tests/seed.sql

clean:
	docker compose down -v

css:
	docker compose exec $(EXEC_FLAGS) web sass static/css/source/screen.scss static/css/screen.css

reset: clean setup
	docker compose down

scry:
	ruff check scrying
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

test-django: lint-django
	docker compose exec $(EXEC_FLAGS) web pytest

test-sync-integration:
	shellcheck tests/*.sh
	awk -f tests/check-line-length.awk tests/*.sh
	bats tests/*.bats

test: test-django test-sync-integration

terraform-plan:
	cd deploy/terraform && terraform plan

terraform-apply:
	cd deploy/terraform && terraform apply

ansible-bootstrap:
	cd deploy/ansible && ansible-playbook bootstrap.yml

ansible-os:
	cd deploy/ansible && ansible-playbook os.yml

ansible-app:
	cd deploy/ansible && ansible-playbook app.yml

build:
	docker build --platform linux/amd64 --target prod --build-arg GIT_SHA=$$(git rev-parse --short HEAD) -t ghcr.io/your5e/your5e:latest .
	docker push ghcr.io/your5e/your5e:latest

deploy:
	cd deploy/ansible && ansible-playbook app.yml

update-notebooks:
	ssh your5e.com 'docker exec $$(docker ps -q -f name=your5e_web) python manage.py import_notebook --all'
