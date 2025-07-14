# Start Docker Services

Start all COTAI Docker services in development mode.

## Usage
`/start` - Start all services
`/start backend` - Start only backend services  
`/start frontend` - Start only frontend
`/start services` - Start only core services (postgres, mongodb, redis)

## Commands Executed

### All Services
```bash
docker-compose up -d
```

### Backend Only
```bash
docker-compose up -d postgres mongodb redis
docker-compose up backend
```

### Frontend Only
```bash
docker-compose up frontend
```

### Core Services Only
```bash
docker-compose up -d postgres mongodb redis
```

## Post-Start Actions
- Check service health at http://localhost:8000/health
- Frontend available at http://localhost:3000
- Check logs with `docker-compose logs -f [service]`