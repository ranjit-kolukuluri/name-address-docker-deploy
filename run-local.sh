# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Enhanced Address Validator - Local Docker Deployment${NC}"

check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is running${NC}"
}

check_env() {
    # 🔧 FIXED: Check for both .env.local and .env
    if [ -f .env.local ]; then
        ENV_FILE=".env.local"
        echo -e "${GREEN}✅ Using .env.local environment file${NC}"
    elif [ -f .env ]; then
        ENV_FILE=".env"
        echo -e "${GREEN}✅ Using .env environment file${NC}"
    else
        echo -e "${YELLOW}⚠️ No environment file found (.env.local or .env)${NC}"
        echo -e "${YELLOW}Please create one from .env.example and add your USPS credentials${NC}"
        exit 1
    fi
}

# 🔧 FIXED: Check dictionary setup
check_dictionaries() {
    if [ -d "dictionaries" ] && [ "$(ls -A dictionaries 2>/dev/null)" ]; then
        echo -e "${GREEN}✅ Dictionary files found in ./dictionaries${NC}"
        echo -e "${BLUE}   Files: $(ls dictionaries | tr '\n' ' ')${NC}"
    else
        echo -e "${YELLOW}⚠️ No dictionary files found in ./dictionaries${NC}"
        echo -e "${YELLOW}   Will use AI-only validation${NC}"
        
        # Create empty directory to prevent Docker copy errors
        mkdir -p dictionaries
        touch dictionaries/.placeholder
    fi
}

# 🔧 FIXED: Better service startup with dictionary check
start_services() {
    echo -e "${YELLOW}🔨 Building Docker images...${NC}"
    docker-compose --env-file $ENV_FILE build
    
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    docker-compose --env-file $ENV_FILE up -d
    
    # Wait for services to start
    echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
    sleep 10
    
    # Check service health
    check_service_health
}

# 🔧 FIXED: Add service health checking
check_service_health() {
    echo -e "${YELLOW}🔍 Checking service health...${NC}"
    
    # Check API health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API server is healthy${NC}"
        
        # Get dictionary status from API
        DICT_STATUS=$(curl -s http://localhost:8000/health | grep -o '"dictionary_loaded":[^,]*' | cut -d':' -f2)
        if [ "$DICT_STATUS" = "true" ]; then
            echo -e "${GREEN}✅ Dictionary validation enabled${NC}"
        else
            echo -e "${YELLOW}⚠️ Using AI-only validation (no dictionaries)${NC}"
        fi
    else
        echo -e "${RED}❌ API server not responding${NC}"
    fi
    
    # Check Streamlit health
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Streamlit UI is healthy${NC}"
    else
        echo -e "${RED}❌ Streamlit UI not responding${NC}"
    fi
    
    echo -e "${GREEN}✅ Services started successfully!${NC}"
    echo -e "${BLUE}🌐 Access Your Services:${NC}"
    echo -e "  • Streamlit UI: ${GREEN}http://localhost:8501${NC}"
    echo -e "  • FastAPI Backend: ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  • Health Check: ${GREEN}http://localhost:8000/health${NC}"
}

stop_services() {
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# 🔧 FIXED: Add dictionary status checking
show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    docker-compose ps
    
    echo -e "\n${BLUE}🔍 Health Status:${NC}"
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API: Running${NC}"
        curl -s http://localhost:8000/health | jq '.' 2>/dev/null || curl -s http://localhost:8000/health
    else
        echo -e "${RED}❌ API: Not responding${NC}"
    fi
    
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Streamlit: Running${NC}"
    else
        echo -e "${RED}❌ Streamlit: Not responding${NC}"
    fi
}

case "$1" in
    "start")
        check_docker
        check_env
        check_dictionaries
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        check_dictionaries
        start_services
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        show_status
        ;;
    "health")
        check_service_health
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|health}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show service logs"
        echo "  status   - Show service status"
        echo "  health   - Check service health"
        exit 1
        ;;
esac