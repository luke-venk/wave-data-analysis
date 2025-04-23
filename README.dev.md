We can use this README as a workspace to take notes on certain things that don't make sense to go into the README, which should be more high-level and designed for end-users.

# Kubernetes
prod: production-ready configuraiton
test: lighter weight or temporary config for test/staging environments

deployments: long-running applications for containers of Flask API, worker, and Redis DB
services: expose deployments to other pods or the outside world
ingress (Flask only): used for HTTP routing
pvc (Redis only): ensures Redis data is stored on disk and survives pod restarts