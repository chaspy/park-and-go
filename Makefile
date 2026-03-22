.PHONY: dev dev-local build-web setup setup-backend setup-web test lint

dev: build-web ## Build web UI and start backend (single port, Tailscale ready)
	cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload

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
