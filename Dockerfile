# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set the working directory in the container
WORKDIR /home

# Copy pyproject.toml first for better caching
COPY pyproject.toml /home/

# Install dependencies using uv
RUN uv sync --no-dev

# Copy the rest of the application
COPY . /home

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV NAME=World

# Run streamlit when the container launches
CMD ["uv", "run", "streamlit", "run", "home.py", "--server.port=8501", "--server.address=0.0.0.0"]