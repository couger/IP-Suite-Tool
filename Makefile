PYTHON ?= python

.PHONY: help test check build dev install-deps
help:
	@echo "make test | check | build | dev | install-deps"
test:
	$(PYTHON) -m pytest -q
check:
	$(PYTHON) scripts/check_public_content.py
build:
	$(PYTHON) scripts/build.py
dev:
	$(PYTHON) scripts/build.py --mode development
install-deps:
	$(PYTHON) -m pip install -r requirements-dev.txt
