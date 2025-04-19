# Base image is Python 3.12
FROM python:3.12

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r ./requirements.txt

# Copy files over into working directory
COPY src/* ./src/
COPY test/* ./test/

# Set entrypoint to run with Python executable
ENTRYPOINT [ "python" ]