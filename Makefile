install:
	poetry install
	pnpm install
	poetry run flask --app borgdrone db init
	sass --update ./borgdrone/static/scss/main.scss ./borgdrone/static/css/main.css

sass:
	sass --update ./borgdrone/static/scss/bootstrap.scss ./borgdrone/static/css/bootstrap.css

sass-watch:
	sass --watch ./borgdrone/static/scss/bootstrap.scss ./borgdrone/static/css/bootstrap.css

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
