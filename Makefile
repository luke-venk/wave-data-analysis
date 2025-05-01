prod: image-push k8s-prod-apply k8s-prod-restart

test: image-push k8s-test-apply k8s-test-restart

docker: dc-down dc-up

image-push:
	docker build -t lukevenk1/wave-data-analysis:1.0 .
	docker push lukevenk1/wave-data-analysis:1.0

k8s-prod-apply:
	kubectl apply -f kubernetes/prod/

k8s-prod-restart:
	kubectl rollout restart deployment app-prod-deployment-flask
	kubectl rollout restart deployment app-prod-deployment-worker

k8s-test-apply:
	kubectl apply -f kubernetes/test/

k8s-test-restart:
	kubectl rollout restart deployment app-test-deployment-flask
	kubectl rollout restart deployment app-test-deployment-worker

dc-down:
	docker compose down

dc-up:
	docker compose up --build
