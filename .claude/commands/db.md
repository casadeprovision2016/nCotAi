# Database Operations Commands

Manage PostgreSQL, MongoDB, and Redis databases for COTAI.

## Usage
`/db` - Connect to all databases
`/db postgres` - PostgreSQL operations
`/db mongo` - MongoDB operations  
`/db redis` - Redis operations
`/db migrate` - Run database migrations
`/db init` - Initialize databases
`/db backup` - Backup databases

## Commands Executed

### Connect to Databases
```bash
# PostgreSQL
docker exec -it cotai-postgres psql -U cotai -d cotai

# MongoDB
docker exec -it cotai-mongodb mongosh -u cotai -p cotai

# Redis
docker exec -it cotai-redis redis-cli
```

### PostgreSQL Operations
```bash
# Connect to PostgreSQL
docker exec -it cotai-postgres psql -U cotai -d cotai

# Run migrations
cd backend
poetry shell
alembic upgrade head
alembic revision --autogenerate -m "migration description"

# Initialize database
docker exec -it cotai-postgres psql -U cotai -d cotai -f /docker-entrypoint-initdb.d/init.sql
python backend/scripts/init_db.py

# Backup
docker exec cotai-postgres pg_dump -U cotai cotai > backup.sql

# Restore
docker exec -i cotai-postgres psql -U cotai -d cotai < backup.sql
```

### MongoDB Operations
```bash
# Connect to MongoDB
docker exec -it cotai-mongodb mongosh -u cotai -p cotai

# Backup
docker exec cotai-mongodb mongodump --db cotai --out /tmp/backup

# Restore
docker exec cotai-mongodb mongorestore --db cotai /tmp/backup/cotai

# Initialize collections
docker exec -it cotai-mongodb mongosh -u cotai -p cotai /docker-entrypoint-initdb.d/init-mongodb.js
```

### Redis Operations
```bash
# Connect to Redis
docker exec -it cotai-redis redis-cli

# Check Redis health
docker exec cotai-redis redis-cli ping

# Monitor Redis
docker exec cotai-redis redis-cli monitor

# Backup
docker exec cotai-redis redis-cli save
docker cp cotai-redis:/data/dump.rdb ./redis-backup.rdb

# Clear cache
docker exec cotai-redis redis-cli flushall
```

### Database Migrations
```bash
cd backend
poetry shell
alembic upgrade head
alembic revision --autogenerate -m "add new tables"
alembic history
alembic current
```

### Initialize All Databases
```bash
# Run initialization scripts
docker exec -it cotai-postgres psql -U cotai -d cotai -f /docker-entrypoint-initdb.d/init.sql
docker exec -it cotai-mongodb mongosh -u cotai -p cotai /docker-entrypoint-initdb.d/init-mongodb.js
python backend/scripts/init_db.py
```

### Backup All Databases
```bash
# PostgreSQL backup
docker exec cotai-postgres pg_dump -U cotai cotai > backup_$(date +%Y%m%d_%H%M%S).sql

# MongoDB backup
docker exec cotai-mongodb mongodump --db cotai --out /tmp/backup_$(date +%Y%m%d_%H%M%S)

# Redis backup
docker exec cotai-redis redis-cli save
docker cp cotai-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb
```

## Connection Details
- **PostgreSQL**: localhost:5432 (cotai/cotai)
- **MongoDB**: localhost:27017 (cotai/cotai)  
- **Redis**: localhost:6379