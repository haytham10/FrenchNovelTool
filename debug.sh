#!/bin/bash

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  French Novel Tool Debug Environment   ${NC}"
echo -e "${GREEN}=========================================${NC}"

if [ "$1" == "backend" ]; then
  echo -e "${YELLOW}Starting backend debugger...${NC}"
  echo -e "${YELLOW}Connect your IDE to port 5678${NC}"
  
  # Set environment variable to enable debugger
  export ENABLE_DEBUGGER=True
  
  # Start backend with debugger
  docker-compose -f docker-compose.dev.yml stop backend
  docker-compose -f docker-compose.dev.yml up -d backend
  
  echo -e "${GREEN}Backend debugger is ready!${NC}"
  echo -e "${YELLOW}Attach your debugger to localhost:5678${NC}"
  
  # Show logs
  docker-compose -f docker-compose.dev.yml logs -f backend

elif [ "$1" == "frontend" ]; then
  echo -e "${YELLOW}Starting frontend debugger...${NC}"
  echo -e "${YELLOW}Connect your IDE to port 9229${NC}"
  
  # Start frontend with debugger
  docker-compose -f docker-compose.dev.yml exec frontend node --inspect=0.0.0.0:9229 node_modules/.bin/next dev -p 3000 --hostname 0.0.0.0
  
  echo -e "${GREEN}Frontend debugger is ready!${NC}"
  echo -e "${YELLOW}Attach your debugger to localhost:9229${NC}"

else
  echo -e "${RED}Error: Please specify which component to debug:${NC}"
  echo -e "${YELLOW}Usage: ./debug.sh [backend|frontend]${NC}"
  exit 1
fi