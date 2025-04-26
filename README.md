# Luke this is what you asked for:

#### Format:
```bash
curl "http://localhost:5000/waves?epoch=MM/DD/YYYY%20HH:MM"
```
### Example: 
```bash
curl "http://localhost:5000/waves?epoch=09/12/2017%2018:30"
```
### Example Output:
```
{
  "Date/Time": "09/12/2017 18:30",
  "Hs": 1.318,
  "Hmax": 2.11,
  "Tz": 4.693,
  "Tp": 5.356,
  "Peak Direction": 23.0,
  "SST": 20.95
}
```
# Analysis of Oceanographic Wave Data from Buoys
TODO: @Tavishka

# Wave Data Analysis

## Overview
This application processes and analyzes ocean wave measurement data collected by buoys off the coast of Mooloolaba, Australia. The application is containerized using Docker and orchestrated using Kubernetes. It provides a Flask web API for interacting with wave data, asynchronous job handling via Redis and HotQueue, and supports deployment on local hardware (e.g., Jetstream) and Kubernetes clusters.

This project builds a production-ready, scalable microservices architecture integrating:
- Dynamic loading of datasets from remote sources.
- Data persistence and queueing with Redis.
- Job management and asynchronous analysis.
- Clear API routes for CRUD operations and on-demand analysis.

## Repository Structure
```
wave-data-analysis/
├── data/
│   └── .gitcanary                # Keeps /data folder tracked by Git
├── diagram.png                     # Architecture diagram
├── docker-compose.yml              # Compose file for local development
├── Dockerfile                      # Build file for Flask application container
├── kubernetes/
│   ├── prod/                      # Kubernetes production manifests
│   └── test/                      # Kubernetes testing manifests
├── Makefile                        # Automation commands (build, run, deploy)
├── README.md                       # Project instructions and overview
├── requirements.txt                # Python dependencies
├── src/                            # Source code
│   ├── flask_api.py                # Flask API defining all endpoints
│   ├── jobs.py                    # Job management functions
│   └── worker.py                  # Worker process to execute jobs
└── test/                         # Unit and integration tests
    ├── test_flask_api.py
    ├── test_jobs.py
    └── test_worker.py
```

## Data Source
- **Kaggle Dataset:** [Wave Measuring Buoys Data (Mooloolaba)](https://www.kaggleusercontent.com/api/v1/datasets/download/jolasa/waves-measuring-buoys-data-mooloolaba)
- **Contents:**
  - Timestamped records of wave height, maximum height, peak period, sea surface temperature, and more.

The app downloads and processes the dataset dynamically at runtime using HTTP requests and Python's `zipfile` module — no manual uploads needed!

## Software Architecture Diagram
![Software Architecture Diagram](diagram.png)

## Flask API Endpoints

### 1. `/help` (GET)
- Returns a description of available routes and their usage.

**Example:**
```bash
curl localhost:5000/help
```

---

### 2. `/data` (POST)
- Populates Redis with fresh wave data from Kaggle.
- If database is already populated, it will skip reloading.

**Example:**
```bash
curl -X POST localhost:5000/data
```

---

### 3. `/data` (GET)
- Retrieves all wave data currently stored in Redis.

**Example:**
```bash
curl localhost:5000/data
```

---

### 4. `/data` (DELETE)
- Clears all wave data from Redis.

**Example:**
```bash
curl -X DELETE localhost:5000/data
```

---

### 5. `/waves?epoch=<timestamp>` (GET)
- Fetches the wave measurement record closest to a provided timestamp.
- Timestamp format: `MM/DD/YYYY HH:MM`

**Example:**
```bash
curl "localhost:5000/waves?epoch=09/12/2017%2018:30"
```

---

### 6. `/jobs` (POST)
- Submits a job for analyzing the wave data.
- Job types include "statistics" or "plot" for a given month/year.

**Payload Example:**
```bash
curl -X POST localhost:5000/jobs -H "Content-Type: application/json" -d '{"month": 9, "year": 2017, "method": "stats"}'
```

---

### 7. `/jobs` (GET)
- Lists all current jobs.

**Example:**
```bash
curl localhost:5000/jobs
```

---

### 8. `/results/<jobid>` (GET)
- Retrieves the result of a completed job.

**Example:**
```bash
curl localhost:5000/results/<jobid>
```

---

### 9. `/keys` (GET)
- Lists all Redis keys for administrative/debugging purposes.

**Example:**
```bash
curl localhost:5000/keys
```

---

## Deployment Instructions

### Local Deployment (Docker Compose)

1. **Clone the Repository:**
```bash
git clone git@github.com:luke-venk/wave-data-analysis.git
cd wave-data-analysis
```

2. **Build and Start Services:**
```bash
docker-compose up --build
```
- This launches Flask, Redis, and the Worker containers.

3. **Stopping the Containers:**
```bash
docker-compose down
```

4. **Reload Dataset:**
```bash
curl -X POST localhost:5000/data
```

5. **Running Tests:**
```bash
docker exec -it <flask-container-name> pytest
```

---

### Kubernetes Deployment (Jetstream, Cloud VMs)

#### Testing Deployment
```bash
kubectl apply -f kubernetes/test/
```
- Deploys minimal resource versions of Flask, Redis, and Worker services for testing.

#### Production Deployment
```bash
kubectl apply -f kubernetes/prod/
```
- Deploys full production-grade services, persistent Redis storage (PVC), and ingress controllers.

#### Port Forwarding (for local testing)
```bash
kubectl port-forward service/flask-service 5000:5000
```

#### Access Public Endpoint
- After configuring ingress:
```bash
curl http://<your-public-endpoint>/help
```

---

## Running Containerized Unit Tests

To execute unit and integration tests:
```bash
docker exec -it <flask-container-name> pytest
```

- Expected output:
```
================== test session starts ==================
collected 18 items

... (some skipped/failing if routes or jobs missing)

=================== X passed, Y failed ==================
```

Test coverage includes:
- Basic route accessibility
- Job creation and retrieval
- Wave statistics and plotting behavior
- Redis connection validation

## Additional Notes
- Redis must be running for most Flask routes to succeed.
- The worker service continuously polls the Redis queue and processes jobs asynchronously.
- When using the `/jobs` endpoint, results become available once the worker completes processing.

## AI Usage Disclaimer
Limited AI assistance was used solely for troubleshooting and understanding errors in the code throughout the development process. All core code and architecture were developed by the project team.

---


