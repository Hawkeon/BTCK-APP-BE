# Bill Split Backend

FastAPI backend cho ứng dụng chia bill - Docker Deployment

## 🚀 Quick Start

```bash
# 1. Copy environment file (uses defaults)
cp .env.example .env

# 2. Start services (DB + Backend)
docker-compose up -d

# 3. Check logs
docker-compose logs -f backend

# 4. Done! API ready at http://localhost:8000
```

## 📋 Requirements

- Docker & Docker Compose v2+
- (No Python needed locally)

## 🔧 Configuration

Edit `.env` file:

```bash
# Database (defaults work for local dev)
POSTGRES_DB=billsplit
POSTGRES_USER=billsplit
POSTGRES_PASSWORD=billsplit123

# Security - change this for production!
SECRET_KEY=your-secret-key-here
FIRST_SUPERUSER_PASSWORD=YourSecurePassword123

# CORS - allow your mobile app origin
BACKEND_CORS_ORIGINS="http://localhost,http://your-phone-ip:8000"
```

## 🌐 Access Points

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| pgAdmin | http://localhost:5050 (if enabled) |

## 🔐 Default Admin Login

- Email: `admin@billsplit.local`
- Password: `Admin123!@#`

## 🛠️ Development

### View logs
```bash
docker-compose logs -f backend
docker-compose logs -f db
```

### Restart services
```bash
docker-compose restart backend
```

### Stop services
```bash
docker-compose down
```

### Clear all data (WARNING: deletes all data)
```bash
docker-compose down -v
docker-compose up -d
```

## 📁 Project Structure

```
├── compose.yml          # Docker Compose configuration
├── .env                 # Environment variables (git-ignored)
├── .env.example         # Example environment file
├── backend/
│   ├── Dockerfile       # Container build config
│   ├── app/
│   │   ├── main.py      # FastAPI app entry
│   │   ├── models.py    # Database models
│   │   ├── crud.py       # Database operations
│   │   └── api/routes/  # API endpoints
│   └── alembic/          # Database migrations
```

## 🔌 API Endpoints

### Auth
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/users/signup` - Register

### Users
- `GET /api/v1/users/me` - Current user
- `PUT /api/v1/users/me` - Update profile
- `POST /api/v1/users/me/qr-code` - Upload QR code
- `GET /api/v1/users/search?email=X` - Search users

### Events
- `GET /api/v1/events` - List user's events
- `POST /api/v1/events` - Create event
- `GET /api/v1/events/{id}` - Get event
- `POST /api/v1/events/{id}/members` - Add member by email
- `GET /api/v1/events/{id}/balances` - Get balances

### Expenses
- `GET /api/v1/events/{id}/expenses` - List expenses
- `POST /api/v1/events/{id}/expenses` - Create expense
- `DELETE /api/v1/events/{id}/expenses/{id}` - Delete expense

### Settlements
- `GET /api/v1/events/{id}/settlements` - List settlements
- `POST /api/v1/events/{id}/settlements` - Record settlement

## 🐛 Troubleshooting

### Database connection errors
```bash
# Check if DB is running
docker-compose ps db

# Check DB logs
docker-compose logs db

# Wait longer for DB to start
docker-compose up -d db && sleep 10 && docker-compose up -d
```

### Migration errors
```bash
# Manually run migrations
docker-compose exec backend alembic upgrade head
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d
```