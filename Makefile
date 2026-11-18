PY := .venv/bin/python

.PHONY: all setup download load report test clean

all: download load report test

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

download:
	$(PY) -m pipeline.download

load:
	$(PY) -m pipeline.load

report:
	$(PY) -m analysis.report

test:
	$(PY) -m pytest -q

clean:
	rm -f data/swiss_power.duckdb
