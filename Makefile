.PHONY: up down logs doctor seed test backup

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

doctor:
	docker compose exec api signalgraph doctor

seed:
	docker compose exec api signalgraph seed-demo

test:
	python -m pytest backend/tests
	cd frontend && npm test && npm run build

backup:
	docker compose exec -T postgres pg_dump -U $${POSTGRES_USER:-signalgraph} -d $${POSTGRES_DB:-signalgraph} -Fc > signalgraph.dump
