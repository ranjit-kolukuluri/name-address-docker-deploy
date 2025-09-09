#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Address Validator - Local Docker Deployment${NC}"

check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

check_env() {
    if [ ! -f .env.local ]; then
        echo -e "${YELLOW}⚠️  .env.local file not found.${NC}"
        echo -e "${YELLOW}Please create it from .env.example and add your USPS credentials${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Environment file found${NC}"
}

start_services() {
    echo -e "${YELLOW}🔨 Building Docker images...${NC}"
    docker-compose --env-file .env.local build

    echo -e "${YELLOW}🚀 Starting services...${NC}"
    docker-compose --env-file .env.local up -d

    echo -e "${GREEN}✅ Services started successfully!${NC}"
    echo -e "${BLUE}🌐 Access Your Services:${NC}"
    echo -e "  • Streamlit UI: ${GREEN}http://localhost:8501${NC}"
    echo -e "  • FastAPI Backend: ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

case "$1" in
    "start")
        check_docker
        check_env
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_services
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status}"
        exit 1
        ;;
esac