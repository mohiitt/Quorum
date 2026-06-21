.PHONY: install test lint demo api dashboard up

install:
	python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

test:
	source .venv/bin/activate && pytest -q

lint:
	source .venv/bin/activate && ruff check quorum tests

api:
	source .venv/bin/activate && uvicorn quorum.api.main:app --reload --port 8000

dashboard:
	cd dashboard && npm run dev

demo:
	source .venv/bin/activate && python -m quorum.agents.demo_workflow

up:
	docker-compose up -d redis && sleep 2 && \
	source .venv/bin/activate && uvicorn quorum.api.main:app --reload &\
	cd dashboard && npm run dev
