# Multiuser Webchat

[![CI](https://github.com/hhoikoo/multiuser-webchat/actions/workflows/ci.yml/badge.svg)](https://github.com/hhoikoo/multiuser-webchat/actions/workflows/ci.yml)

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
- **Observability**: Prometheus metrics with Grafana dashboards for monitoring

## Technology Stack

- **Backend**: Python 3.13, aiohttp, Redis
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Infrastructure**: Docker, Nginx, Redis, Prometheus, Grafana
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

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Grafana   │◄───│ Prometheus  │◄───│  Chat App   │
│  :3001      │    │  :9091      │    │  /metrics   │
└─────────────┘    └─────────────┘    └─────────────┘
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
   cd multiuser-webchat
   ```

1. **Start the application**:

   ```bash
   docker compose up -d
   ```

1. **Access the application**:
   Open your browser and navigate to `http://localhost:8080`

1. **Scale the application** (optional):

   ```bash
   WEB_REPLICAS=8 docker compose up -d --scale web=8
   ```

1. **Stop the application**:

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

1. **Set up Python environment**:

   ```bash
   # Install Python 3.13 with pyenv
   pyenv install 3.13

   # Set local Python version for this project
   pyenv local 3.13

   # Verify Python version
   python --version
   ```

1. **Install dependencies**:

   ```bash
   pants --version
   ```

1. **Start Redis**:

   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis:7-alpine

   # Or install Redis locally and start it
   redis-server
   ```

1. **Run the application**:

   ```bash
   # Development mode
   pants run src/server:app -- --host 0.0.0.0 --port 8080 --workers 1 --redis-url redis://localhost:6379

   # Or build and run PEX
   ./pants package src/server:app
   python dist/src.server/app.pex --host 0.0.0.0 --port 8080
   ```

1. **Access the application**:
   Open your browser and navigate to `http://localhost:8080`

### Environment Variables

You can customize the application behavior using environment variables:

| Variable                   | Default                     | Description                                               |
| -------------------------- | --------------------------- | --------------------------------------------------------- |
| `HOST`                     | `0.0.0.0`                   | Server bind address                                       |
| `PORT`                     | `8080`                      | Server port                                               |
| `WORKERS`                  | `1`                         | Number of worker processes                                |
| `REDIS_URL`                | `redis://localhost:6379`    | Redis connection URL                                      |
| `WEB_REPLICAS`             | `4`                         | (Only in `docker-compose`) Number of web service replicas |
| `PROMETHEUS_MULTIPROC_DIR` | `/tmp/prometheus_multiproc` | Directory for Prometheus multiprocess metrics             |

Example:

```bash
# Run with custom settings
HOST=127.0.0.1 PORT=3000 WORKERS=4 pants run src/server:app
```

## Development

### Setting Up Pre-Commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to automatically run code quality checks before each commit.

#### Installation

1. **Install pre-commit**:

   ```bash
   # Using pip
   pip install pre-commit

   # Or using Homebrew (macOS)
   brew install pre-commit
   ```

1. **Install the git hook scripts**:

   ```bash
   pre-commit install
   ```

1. **Verify installation** (optional):

   ```bash
   # Run against all files to test
   pre-commit run --all-files
   ```

#### Usage

Once installed, pre-commit hooks run automatically before each commit. If any checks fail:

1. Review the error messages
1. Fix the issues (many are auto-fixed)
1. Stage the fixed files: `git add .`
1. Commit again: `git commit -m "your message"`

#### Manual Execution

Run hooks manually without committing:

```bash
# Run on all files
pre-commit run --all-files

# Run on specific files
pre-commit run --files src/server/app.py

# Run a specific hook
pre-commit run pants-fmt --all-files
```

#### Updating Hooks

Keep hooks up to date:

```bash
# Update to latest versions
pre-commit autoupdate
```

### Project Structure

```
multiuser-webchat/
├── src/server/           # Python backend application
│   ├── app.py           # Main application entry point
│   ├── ws.py            # WebSocket handling
│   ├── models.py        # Data models
│   ├── redis.py         # Redis connection management
│   └── metrics.py       # Prometheus metrics definitions
├── frontend/static/      # Frontend assets
│   ├── index.html       # Main HTML page
│   ├── app.js          # WebSocket client with auto-reconnection
│   └── style.css       # Styles
├── monitoring/           # Observability configuration
│   ├── prometheus/      # Prometheus config
│   └── grafana/         # Grafana dashboards and datasources
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

1. **Scaling**:

   - Adjust `WEB_REPLICAS` based on expected load
   - Monitor Redis memory usage and configure persistence if needed
   - Consider Redis Cluster for high availability

1. **Monitoring**:

   - Application exposes health check endpoints at `/healthz`
   - Prometheus metrics available at `/metrics`
   - Grafana dashboards for real-time monitoring
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

## Monitoring

The application includes built-in observability with Prometheus metrics and Grafana dashboards.

### Accessing Dashboards

- **Grafana**: `http://localhost:3001` (anonymous access enabled)
- **Prometheus**: `http://localhost:9091`

### Available Metrics

The application exposes the following metrics at `/metrics`:

| Metric                            | Type      | Description                                     |
| --------------------------------- | --------- | ----------------------------------------------- |
| `webchat_connected_users`         | Gauge     | Number of currently connected WebSocket users   |
| `webchat_messages_total`          | Counter   | Total number of messages processed              |
| `webchat_message_latency_seconds` | Histogram | Time to process a message                       |
| `webchat_connections_total`       | Counter   | Total WebSocket connection attempts (by status) |
| `webchat_disconnections_total`    | Counter   | Total WebSocket disconnections (by reason)      |
| `webchat_redis_operations_total`  | Counter   | Total Redis operations (by operation/status)    |
| `webchat_redis_latency_seconds`   | Histogram | Redis operation latency                         |
| `webchat_errors_total`            | Counter   | Total errors (by type)                          |

### Docker Service Discovery

Prometheus uses Docker service discovery to automatically find and scrape all web container replicas. This means:

- No manual configuration needed when scaling workers
- Metrics are collected directly from each container (not through nginx)
- Use `sum(webchat_connected_users)` in PromQL to get total connected users across all replicas

## Troubleshooting

### Common Issues

1. **WebSocket connection failed**:

   - Ensure Redis is running and accessible
   - Check Docker container logs: `docker compose logs web`
   - Verify port 8080 is not in use by another application

1. **Messages not appearing for all users**:

   - Confirm Redis is properly configured for pub/sub
   - Check that multiple application instances are connecting to the same Redis instance

1. **Build failures**:

   - Ensure Python 3.13 is available in the build environment
   - Check that all dependencies in `pyproject.toml` are accessible

### Health Checks

- **Application**: `http://localhost:8080/healthz`
- **Nginx**: Monitors application health and fails over accordingly
- **Redis**: Built-in health check via `redis-cli ping`

## Continuous Integration

This project uses GitHub Actions for automated CI/CD. The pipeline runs on every push and pull request, checking:

- Code formatting and linting (Ruff)
- Type checking (MyPy)
- Tests with Redis integration
- Security scanning (Gitleaks)
- Application builds (PEX and Docker)

Check the [Actions tab](https://github.com/hhoikoo/multiuser-webchat/actions) to view workflow runs. CI checks must pass before pull requests can be merged.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Contributing

1. Fork the repository
1. Create a feature branch: `git checkout -b feature-name`
1. Make your changes and ensure tests pass: `pants test ::`
1. Run code quality checks: `pants fmt lint check ::`
1. Commit your changes: `git commit -am 'Add feature'`
1. Push to the branch: `git push origin feature-name`
1. Submit a pull request (CI will run automatically)
