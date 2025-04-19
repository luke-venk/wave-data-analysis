all: down up

down:
	docker compose down

up:
	docker compose up --build
