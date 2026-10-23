.PHONY: install run test wishlist orders

PYTHON ?= python3
PIZZA_DB_PATH ?= $(HOME)/pizza-db/build/pizza.db
export PIZZA_DB_PATH

install:
	$(PYTHON) -m pip install -r backend/requirements-dev.txt

run:
	cd backend && $(PYTHON) -m uvicorn app.main:create_app --factory --reload --port 8000

test:
	cd backend && $(PYTHON) -m pytest -q

wishlist:
	cd backend && $(PYTHON) -m app.admin wishlist

orders:
	cd backend && $(PYTHON) -m app.admin orders --limit 10
