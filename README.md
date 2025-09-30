# Bootcamp Webchat

(README generated with Claude Code)

A real-time multi-user webchat application built with Python (aiohttp), Redis, and vanilla JavaScript. This application demonstrates modern web technologies including WebSockets, containerization, and load balancing.

## Features

- **Real-time messaging**: Instant message delivery using WebSockets
- **Multi-user support**: Multiple users can chat simultaneously in a single room
- **Automatic reconnection**: Client automatically reconnects on connection loss with exponential backoff
- **Scalable architecture**: Horizontally scalable using Redis pub/sub for inter-process communication
- **Load balancing**: Nginx reverse proxy with support for multiple backend instances
- **Containerized deployment**: Full Docker Compose setup for easy deployment
- **Health checks**: Built-in health monitoring for all services

## Technology Stack

- **Backend**: Python 3.13, aiohttp, Redis
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Infrastructure**: Docker, Nginx, Redis
- **Build System**: Pants build system
- **Code Quality**: Ruff (linting/formatting), MyPy (type checking)

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Browser   │◄──►│    Nginx    │◄──►│  Chat App   │
│             │    │ (Load Bal.) │    │ (Multiple)  │
└─────────────┘    └─────────────┘    └─────────────┘
                           │                  │
                           │                  ▼
                           │          ┌─────────────┐
                           │          │    Redis    │
                           │          │  (Pub/Sub)  │
                           │          └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Static    │
                   │    Files    │
                   └─────────────┘
```

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher

### For Local Development (Optional)
- **Python**: 3.13.x (Recommended: [pyenv](https://github.com/pyenv/pyenv#installation))
- **Pants**: Build system ([link](https://www.pantsbuild.org/dev/docs/getting-started/installing-pants))
- **Redis**: For local Redis instance (if not using Docker)

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bootcamp-webchat
   ```

2. **Start the application**:
   ```bash
   docker compose up -d
   ```

3. **Access the application**:
   Open your browser and navigate to `http://localhost:8080`

4. **Scale the application** (optional):
   ```bash
   WEB_REPLICAS=8 docker compose up -d --scale web=8
   ```

5. **Stop the application**:
   ```bash
   docker compose down
   ```

### Build from Source

If you prefer to build the Docker image manually:

```bash
# Build the image
docker build -t chat-app:latest .

# Run with Docker Compose
docker compose up -d
```

## Alternative Running Methods

### Local Development with Pants

For development without Docker:

1. **Install dependencies**:
   ```bash
   pants --version
   ```

2. **Start Redis**:
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine

   # Or install Redis locally and start it
   redis-server
   ```

3. **Run the application**:
   ```bash
   # Development mode
   pants run src/server:app -- --host 0.0.0.0 --port 8080 --workers 1 --redis-url redis://localhost:6379

   # Or build and run PEX
   ./pants package src/server:app
   python dist/src.server/app.pex --host 0.0.0.0 --port 8080
   ```

4. **Access the application**:
   Open your browser and navigate to `http://localhost:8080`

### Environment Variables

You can customize the application behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server port |
| `WORKERS` | `1` | Number of worker processes |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `WEB_REPLICAS` | `4` | (Only in `docker-compose`) Number of web service replicas |

Example:
```bash
# Run with custom settings
HOST=127.0.0.1 PORT=3000 WORKERS=4 pants run src/server:app
```

## Development

### Project Structure

```
bootcamp-webchat/
├── src/server/           # Python backend application
│   ├── app.py           # Main application entry point
│   ├── ws.py            # WebSocket handling
│   ├── models.py        # Data models
│   └── redis.py         # Redis connection management
├── frontend/static/      # Frontend assets
│   ├── index.html       # Main HTML page
│   ├── app.js          # WebSocket client with auto-reconnection
│   └── style.css       # Styles
├── tests/               # Test suite
├── docker-compose.yml   # Multi-service Docker setup
├── Dockerfile          # Application container definition
├── nginx.conf          # Nginx load balancer configuration
├── pants.toml          # Pants build configuration
├── mypy.ini            # Type checking configuration
└── ruff.toml           # Linting and formatting configuration
```

### Code Quality

Run linting and type checking:

```bash
# Format code
pants fmt ::

# Lint code
pants lint ::

# Type check
pants check ::

# Run all checks
pants fmt lint check ::
```

### Testing

```bash
# Run all tests
pants test ::

# Run specific test
pants test tests/test_example.py

# Run tests with coverage
pants test --coverage-report=html ::
```

### Building

```bash
# Build PEX executable
pants package src/server:app

# Build Docker image
docker build -t chat-app:latest .
```

## Deployment

### Production Considerations

1. **Security**:
   - Use HTTPS in production (configure SSL termination at Nginx or load balancer)
   - Set secure environment variables
   - Consider using Redis AUTH for Redis connections

2. **Scaling**:
   - Adjust `WEB_REPLICAS` based on expected load
   - Monitor Redis memory usage and configure persistence if needed
   - Consider Redis Cluster for high availability

3. **Monitoring**:
   - Application exposes health check endpoints at `/healthz`
   - Monitor Docker container health status
   - Set up logging aggregation for distributed logs

### Docker Compose Production

For production deployment, consider:

```bash
# Production deployment with scaling
WEB_REPLICAS=8 docker compose -f docker-compose.yml up -d

# View logs
docker compose logs -f

# Monitor health
docker compose ps
```

## Troubleshooting

### Common Issues

1. **WebSocket connection failed**:
   - Ensure Redis is running and accessible
   - Check Docker container logs: `docker compose logs web`
   - Verify port 8080 is not in use by another application

2. **Messages not appearing for all users**:
   - Confirm Redis is properly configured for pub/sub
   - Check that multiple application instances are connecting to the same Redis instance

3. **Build failures**:
   - Ensure Python 3.13 is available in the build environment
   - Check that all dependencies in `pyproject.toml` are accessible

### Health Checks

- **Application**: `http://localhost:8080/healthz`
- **Nginx**: Monitors application health and fails over accordingly
- **Redis**: Built-in health check via `redis-cli ping`

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and ensure tests pass: `pants test ::`
4. Run code quality checks: `pants fmt lint check ::`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request
