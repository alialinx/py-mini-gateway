# py-mini-gateway

Minimal API Gateway built with Python.

## Features
- Path-based routing
- Reverse proxy
- Docker Compose setup
- Request logging with request_id

## Quickstart
docker compose up --build

## Example Requests
curl http://localhost:8000/users/ping
curl http://localhost:8000/orders/ping

## Purpose
This project is built as a learning exercise to understand
API Gateway patterns and DevOps fundamentals.