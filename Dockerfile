# Base image is Python 3.12
FROM python:3.12

# Copy files over into working directory
WORKDIR /app
COPY src/* ./src/
COPY test/* ./test/
COPY requirements.txt ./

# Install dependencies
RUN pip3 install -r ./requirements.txt

# Set entrypoint to run with Python executable
ENTRYPOINT [ "python" ]