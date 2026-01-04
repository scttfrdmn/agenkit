.PHONY: help up down restart logs ps build clean test health backup restore

# Default target
help:
	@echo "Agenkit Docker Compose Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  up              - Start all services"
	@echo "  down            - Stop all services"
	@echo "  restart         - Restart all services"
	@echo "  logs            - View logs (all services)"
	@echo "  ps              - Show service status"
	@echo "  build           - Build custom images"
	@echo "  clean           - Stop and remove all containers, networks, volumes"
	@echo "  test            - Test API endpoints"
	@echo "  health          - Check service health"
	@echo "  backup          - Backup PostgreSQL database"
	@echo "  restore         - Restore PostgreSQL database from backup"
	@echo ""
	@echo "Development:"
	@echo "  dev-up          - Start development stack"
	@echo "  dev-down        - Stop development stack"
	@echo "  dev-logs        - View development logs"
	@echo ""
	@echo "Monitoring:"
	@echo "  grafana         - Open Grafana in browser"
	@echo "  prometheus      - Open Prometheus in browser"
	@echo "  jaeger          - Open Jaeger in browser"
	@echo ""
	@echo "Maintenance:"
	@echo "  scale-python    - Scale Python agents (e.g., make scale-python N=3)"
	@echo "  scale-go        - Scale Go agents (e.g., make scale-go N=3)"
	@echo "  prune           - Clean up Docker system"

# ============================================================
# Core Commands
# ============================================================

up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. Run 'make logs' to view logs."

down:
	@echo "Stopping all services..."
	docker-compose down

restart:
	@echo "Restarting all services..."
	docker-compose restart

logs:
	docker-compose logs -f

ps:
	docker-compose ps

build:
	@echo "Building custom images..."
	docker-compose build --no-cache

clean:
	@echo "WARNING: This will remove all containers, networks, and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all --remove-orphans; \
		echo "Cleanup complete."; \
	else \
		echo "Aborted."; \
	fi

# ============================================================
# Development Mode
# ============================================================

dev-up:
	@echo "Starting development stack..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development stack started."
	@echo "  Python Agent: http://localhost:8000"
	@echo "  Go Agent:     http://localhost:8001"
	@echo "  Redis GUI:    http://localhost:8081"
	@echo "  pgAdmin:      http://localhost:5050"

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# ============================================================
# Testing
# ============================================================

test:
	@echo "Testing API endpoints..."
	@echo ""
	@echo "Testing health endpoint..."
	@curl -s http://localhost:8080/health | jq . || echo "FAILED"
	@echo ""
	@echo "Testing Python agent..."
	@curl -s -X POST http://localhost:8080/api/python/agent \
		-H "Content-Type: application/json" \
		-d '{"message": {"role": "user", "content": "Test"}}' \
		| jq . || echo "FAILED"
	@echo ""
	@echo "Testing Go agent..."
	@curl -s -X POST http://localhost:8080/api/go/agent \
		-H "Content-Type: application/json" \
		-d '{"message": {"role": "user", "content": "Test"}}' \
		| jq . || echo "FAILED"

health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Container stats:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# ============================================================
# Monitoring
# ============================================================

grafana:
	@echo "Opening Grafana..."
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Please open http://localhost:3000"

prometheus:
	@echo "Opening Prometheus..."
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Please open http://localhost:9090"

jaeger:
	@echo "Opening Jaeger..."
	@open http://localhost:16686 || xdg-open http://localhost:16686 || echo "Please open http://localhost:16686"

# ============================================================
# Scaling
# ============================================================

scale-python:
	@if [ -z "$(N)" ]; then \
		echo "Usage: make scale-python N=<number>"; \
		exit 1; \
	fi
	@echo "Scaling Python agents to $(N) instances..."
	@docker-compose up -d --scale agenkit-python=$(N)

scale-go:
	@if [ -z "$(N)" ]; then \
		echo "Usage: make scale-go N=<number>"; \
		exit 1; \
	fi
	@echo "Scaling Go agents to $(N) instances..."
	@docker-compose up -d --scale agenkit-go=$(N)

# ============================================================
# Backup and Restore
# ============================================================

backup:
	@echo "Creating PostgreSQL backup..."
	@mkdir -p backups
	@docker-compose exec -T postgres pg_dump -U agenkit agenkit | gzip > backups/agenkit-$(shell date +%Y%m%d-%H%M%S).sql.gz
	@echo "Backup created: backups/agenkit-$(shell date +%Y%m%d-%H%M%S).sql.gz"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=<backup-file>"; \
		exit 1; \
	fi
	@echo "Restoring PostgreSQL from $(FILE)..."
	@gunzip -c $(FILE) | docker-compose exec -T postgres psql -U agenkit agenkit
	@echo "Restore complete."

# ============================================================
# Maintenance
# ============================================================

prune:
	@echo "Pruning Docker system..."
	docker system prune -af --volumes
	@echo "Prune complete."

# ============================================================
# Individual Service Management
# ============================================================

python-logs:
	docker-compose logs -f agenkit-python

go-logs:
	docker-compose logs -f agenkit-go

nginx-logs:
	docker-compose logs -f nginx

postgres-logs:
	docker-compose logs -f postgres

redis-logs:
	docker-compose logs -f redis

prometheus-logs:
	docker-compose logs -f prometheus

grafana-logs:
	docker-compose logs -f grafana

jaeger-logs:
	docker-compose logs -f jaeger
