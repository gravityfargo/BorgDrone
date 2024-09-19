install:
	python3 -m venv .venv
	pip install -e .
	pip install .[DEV]
	pnpm install
	flask --app borgdrone db init

migrate:
	flask --app borgdrone db migrate -m "Upgrade database."
	flask --app borgdrone db upgrade

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name 'instance' -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '.webassets-cache' -exec rm -rf {} +
	find . -name 'build' -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf migrations
	find . -name 'node_modules' -exec rm -rf {} +
	rm -rf .venv

run:
	flask --app borgdrone run

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
