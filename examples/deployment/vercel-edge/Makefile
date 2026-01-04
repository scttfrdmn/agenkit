.PHONY: help install dev build start deploy deploy-prod test lint type-check clean logs kv-list health

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm install

dev: ## Start development server
	npm run dev

build: ## Build production bundle
	npm run build

start: ## Start production server (after build)
	npm run start

deploy: ## Deploy to Vercel preview
	vercel

deploy-prod: ## Deploy to Vercel production
	vercel --prod

test: ## Run tests
	npm test

lint: ## Run linter
	npm run lint

type-check: ## Run TypeScript type checker
	npm run type-check

clean: ## Clean build artifacts
	rm -rf .next node_modules .vercel

logs: ## Tail production logs
	vercel logs --follow

logs-errors: ## Show recent errors
	vercel logs --output json | jq 'select(.level == "error")'

kv-list: ## List all KV keys
	vercel kv list

kv-sessions: ## Show session keys
	vercel kv list | grep session:

health: ## Check health endpoint
	@curl -s http://localhost:3000/api/health | jq

health-prod: ## Check production health endpoint
	@vercel ls --json | jq -r '.[0].url' | xargs -I {} curl -s https://{}/api/health | jq

test-local: ## Test agent endpoint locally
	@curl -X POST http://localhost:3000/api/agent \
		-H "Content-Type: application/json" \
		-d '{"agent_type":"react","message":{"role":"user","content":"Calculate 10 + 5"}}' | jq

test-prod: ## Test agent endpoint in production
	@vercel ls --json | jq -r '.[0].url' | xargs -I {} curl -X POST https://{}/api/agent \
		-H "Content-Type: application/json" \
		-d '{"agent_type":"react","message":{"role":"user","content":"Calculate 10 + 5"}}' | jq

env-pull: ## Pull environment variables from Vercel
	vercel env pull .env.local

env-ls: ## List environment variables
	vercel env ls

setup-kv: ## Create KV store
	vercel kv create agenkit-sessions

open: ## Open app in browser
	@vercel ls --json | jq -r '.[0].url' | xargs -I {} open https://{}

status: ## Show deployment status
	vercel ls

inspect: ## Inspect latest deployment
	@vercel ls --json | jq -r '.[0].uid' | xargs vercel inspect
