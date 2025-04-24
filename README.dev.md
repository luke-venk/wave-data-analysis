We can use this README as a workspace to take notes on certain things that don't make sense to go into the README, which should be more high-level and designed for end-users.

# Kubernetes
prod: production-ready configuraiton
test: lighter weight or temporary config for test/staging environments

deployments: long-running applications for containers of Flask API, worker, and Redis DB
services: defines how other applications can access our application
- ClusterIP: only accessible inside cluster (only needed internally)
    - Flask and Redis will use this to talk to each other
- NodePort: exposes service on a port on every node's IP
    - Flask will use this so users can make requests from their PC
ingress (Flask only): used for HTTP routing
- a lot prettier than NodePort routing (TCP)
pvc (Redis only): ensures Redis data is stored on disk and survives pod restarts