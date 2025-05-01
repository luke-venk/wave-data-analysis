all: k8s-push k8s-apply k8s-restart

k8s-push:
	docker build -t lukevenk1/wave-data-analysis:1.0 .
	docker push lukevenk1/wave-data-analysis:1.0

k8s-apply:
	kubectl apply -f kubernetes/test/app-test-deployment-flask.yml
	kubectl apply -f kubernetes/test/app-test-deployment-worker.yml

k8s-restart:
	kubectl rollout restart deployment app-test-deployment-flask
	kubectl rollout restart deployment app-test-deployment-worker

dc-down:
	docker compose down

dc-up:
	docker compose up --build
