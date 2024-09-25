install:
	poetry install
	pnpm install
	poetry run flask --app borgdrone db init

migrate:
	poetry run flask --app borgdrone db migrate -m "Upgrade database."
	poetry run flask --app borgdrone db upgrade

clean:
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name 'instance' -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf migrations
	find . -name 'node_modules' -exec rm -rf {} +
	rm -rf .venv

run:
	export PYTESTING=False
	poetry run flask --app borgdrone run

cleanrun:
	make clean
	make install
	make run

test:
	clear
	poetry run pytest

test-repos:
	clear
	poetry run pytest tests/test_repositories.py

test-bundles:
	clear
	poetry run pytest tests/test_bundles.py

test-archives:
	clear
	poetry run pytest tests/test_archives.py
