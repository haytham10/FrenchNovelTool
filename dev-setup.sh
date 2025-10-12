#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  French Novel Tool Development Setup    ${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if .env.dev exists
if [ ! -f .env.dev ]; then
    echo -e "${YELLOW}Creating .env.dev file from template...${NC}"
    cp .env.dev.example .env.dev
    echo -e "${YELLOW}Please edit .env.dev with your API keys and settings${NC}"
    echo -e "${RED}Setup paused: Edit .env.dev first, then run this script again${NC}"
    exit 1
fi

# Check Docker is installed and running
if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker and docker-compose are required but not installed.${NC}"
    echo "Please install Docker Desktop (Windows/Mac) or Docker Engine and Docker Compose (Linux)."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running.${NC}"
    echo "Please start Docker Desktop or the Docker service."
    exit 1
fi

echo -e "${GREEN}Creating development environment...${NC}"

# Build and start containers
echo -e "${YELLOW}Building and starting containers...${NC}"
docker-compose -f docker-compose.dev.yml up -d --build

# Initialize the database
echo -e "${YELLOW}Initializing database...${NC}"
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade

echo -e "${GREEN}Development environment is ready!${NC}"
echo -e "${GREEN}Backend API: http://localhost:5000${NC}"
echo -e "${GREEN}Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}Redis: localhost:6379${NC}"
echo ""
echo -e "${YELLOW}Use these commands to manage the environment:${NC}"
echo -e "  ${GREEN}Start:${NC} docker-compose -f docker-compose.dev.yml up -d"
echo -e "  ${GREEN}Stop:${NC} docker-compose -f docker-compose.dev.yml down"
echo -e "  ${GREEN}View logs:${NC} docker-compose -f docker-compose.dev.yml logs -f"
echo -e "  ${GREEN}Shell access:${NC}"
echo -e "    - Backend: docker-compose -f docker-compose.dev.yml exec backend bash"
echo -e "    - Frontend: docker-compose -f docker-compose.dev.yml exec frontend sh"