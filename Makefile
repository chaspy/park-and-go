PIDFILE := .parking-judge.pid
LOGFILE := .parking-judge.log

.PHONY: dev dev-local build-web start stop restart status logs setup setup-backend setup-web test lint help

dev: build-web ## Build web UI and start backend (foreground)
	cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload

start: build-web ## Start backend in background (survives terminal close)
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "Already running (PID $$(cat $(PIDFILE)))"; \
	else \
		cd backend && source .venv/bin/activate && \
		nohup uvicorn app.main:app --host 0.0.0.0 --port 8787 > ../$(LOGFILE) 2>&1 & \
		echo $$! > ../$(PIDFILE); \
		sleep 1; \
		echo "Started (PID $$(cat ../$(PIDFILE))), log: $(LOGFILE)"; \
	fi

stop: ## Stop background server
	@if [ -f $(PIDFILE) ]; then \
		kill $$(cat $(PIDFILE)) 2>/dev/null && echo "Stopped" || echo "Not running"; \
		rm -f $(PIDFILE); \
	else \
		echo "Not running"; \
	fi

restart: stop start ## Restart background server

status: ## Check if server is running
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "Running (PID $$(cat $(PIDFILE)))"; \
		curl -s http://127.0.0.1:8787/api/health; echo; \
	else \
		echo "Not running"; \
	fi

logs: ## Tail server logs
	@tail -f $(LOGFILE)

dev-local: ## Start backend + Vite dev server separately (for frontend dev)
	@trap 'kill 0' EXIT; \
	cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload & \
	cd web && npm run dev & \
	wait

build-web: ## Build web UI static files
	cd web && npm run build

setup: setup-backend setup-web ## Setup all dependencies

setup-backend: ## Setup backend dependencies
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

setup-web: ## Setup web dependencies
	cd web && npm install

test: ## Run backend tests
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v

lint: ## Run linter
	cd backend && source .venv/bin/activate && ruff check app/ tests/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
