install:
	poetry install
	pnpm install
	poetry run flask --app borgdrone db init

migrate:
	flask --app borgdrone db migrate -m "Upgrade database."
	flask --app borgdrone db upgrade

clean:
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name 'instance' -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf migrations
	find . -name 'node_modules' -exec rm -rf {} +
	rm -rf .venv

run:
	poetry run flask --app borgdrone run

cleanrun:
	make clean
	make run

test-all:
	clear
	pytest

test-repos:
	clear
	pytest tests/requests/test_repositories.py

test-bundles:
	clear
	pytest tests/requests/test_bundles.py
