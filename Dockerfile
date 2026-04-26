# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install clang
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clang \
        clang-tidy \
        clang-format \
        cppcheck \
        llvm \
        gcc \
        valgrind \
        llvm-dev \
        libclang-dev \
        ca-certificates \
        make \
        bear && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set the working directory in the container
WORKDIR /home

# Copy pyproject.toml first for better caching
COPY pyproject.toml /home/

# Install dependencies using uv
RUN uv sync --no-dev

# Added the environment path
ENV PATH="/home/.venv/bin:$PATH"

# Copy the rest of the application
COPY . /home

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV NAME=World

# Disable Python output buffering so print() calls appear immediately in Docker logs
ENV PYTHONUNBUFFERED=1

# Run streamlit when the container launches
CMD ["uv", "run", "streamlit", "run", "home.py", "--server.port=8501", "--server.address=0.0.0.0"]