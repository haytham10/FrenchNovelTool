# French Novel Tool - Local Development Setup

This guide provides instructions for setting up a complete isolated development environment for the French Novel Tool project using Docker containers.

## Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose
- Git
- A code editor (VS Code recommended)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/haytham10/FrenchNovelTool.git
cd FrenchNovelTool
```

### 2. Set up environment variables

```bash
# On Unix/Linux/MacOS
cp .env.dev.example .env.dev

# On Windows
copy .env.dev.example .env.dev
```

Edit `.env.dev` and add your API keys:
- `GEMINI_API_KEY` - For Gemini AI integration
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` - For OAuth authentication

### 3. Start the development environment

```bash
# On Unix/Linux/MacOS
./dev-setup.sh

# On Windows
dev-setup.bat
```

This script will:
1. Create Docker containers for the backend, frontend, and Redis
2. Initialize the database
3. Start all services

### 4. Access the application

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Redis: localhost:6379

## WebSocket Real-Time Updates

The application uses WebSocket for real-time job progress updates. No additional configuration is needed in development - it's automatically enabled.

**Features:**
- Instant progress updates (no polling)
- Automatic reconnection
- Connection status indicator in UI

**Troubleshooting WebSocket:**
- Ensure eventlet is installed: `pip install eventlet`
- Check WebSocket connection in browser DevTools (Network → WS tab)
- Verify JWT token is being sent with connection

See [docs/WEBSOCKET_IMPLEMENTATION.md](docs/WEBSOCKET_IMPLEMENTATION.md) for detailed documentation.

## Development Workflow

### Directory Structure

The repository is mounted into the containers, so any changes you make to the code will be reflected immediately:

- `./backend` → `/app` in the backend container
- `./frontend` → `/app` in the frontend container

### Useful Commands

#### View logs

```bash
docker-compose -f docker-compose.dev.yml logs -f
```

#### Access container shells

```bash
# Backend shell
docker-compose -f docker-compose.dev.yml exec backend bash

# Frontend shell
docker-compose -f docker-compose.dev.yml exec frontend sh
```

#### Run database migrations

```bash
docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "Migration description"
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

#### Install new packages

```bash
# Backend (Python)
docker-compose -f docker-compose.dev.yml exec backend pip install package-name
docker-compose -f docker-compose.dev.yml exec backend pip freeze > backend/requirements.txt

# Frontend (Node.js)
docker-compose -f docker-compose.dev.yml exec frontend npm install package-name
```

#### Run tests

```bash
# Backend tests
docker-compose -f docker-compose.dev.yml exec backend pytest

# Frontend tests
docker-compose -f docker-compose.dev.yml exec frontend npm test
```

### Debugging

#### Backend (Flask)

The backend container includes `debugpy` for Python debugging.

1. Set `ENABLE_DEBUGGER=True` in your `.env.dev` file
2. Restart the container: `docker-compose -f docker-compose.dev.yml restart backend`
3. Connect your IDE debugger to port 5678

#### Frontend (Next.js)

The Node.js debugger is exposed on port 9229.

## Clean Up

To stop and remove all containers:

```bash
docker-compose -f docker-compose.dev.yml down
```

To also remove volumes (this will delete your development database):

```bash
docker-compose -f docker-compose.dev.yml down -v
```

## Troubleshooting

### CORS Issues

- Ensure `CORS_ORIGINS` includes all frontend URLs (default: `http://localhost:3000,http://frontend:3000`)
- Check that the frontend is using the correct backend URL

### Database Issues

- Ensure migrations are applied: `docker-compose -f docker-compose.dev.yml exec backend flask db upgrade`
- To reset the database: `docker-compose -f docker-compose.dev.yml exec backend flask db downgrade base`

### Container Access Issues

- Check container status: `docker-compose -f docker-compose.dev.yml ps`
- Inspect container logs: `docker-compose -f docker-compose.dev.yml logs -f [service_name]`