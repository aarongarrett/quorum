# Quorum Voting System

![Tests](https://github.com/aarongarrett/quorum/actions/workflows/tests.yml/badge.svg)
![E2E Tests](https://github.com/aarongarrett/quorum/actions/workflows/e2e.yml/badge.svg)
![CI & CD](https://github.com/aarongarrett/quorum/actions/workflows/ci.yml/badge.svg)
[![Coverage Status](https://coveralls.io/repos/github/aarongarrett/quorum/badge.svg?branch=main)](https://coveralls.io/github/aarongarrett/quorum?branch=main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Anonymous, QR-driven voting for meetings with FastAPI backend and React frontend.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Development](#development)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Changelog](#changelog)

---

## Overview

Quorum is a secure, anonymous voting system designed for meetings. Built with modern technologies, it provides real-time voting with QR-code check-ins.

**Key Capabilities:**

**Security:**
- Argon2-hashed vote tokens (no plaintext storage)
- JWT-based admin authentication
- Idempotent check-in prevents duplicate tokens
- Foreign key architecture ensures data integrity

**Architecture:**
- FastAPI backend (async, modern Python)
- React SPA frontend (no page reloads)
- Server-Sent Events for real-time updates
- Client-side QR code generation

**User Experience:**
- Tokens stored in localStorage (persist across refreshes)
- Real-time vote count updates
- Automatic reconnection on network issues
- Comprehensive error handling and loading states

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo>
cd quorum

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost:8000
# Admin: http://localhost:8000/admin
# API Docs: http://localhost:8000/docs
```

That's it! The database tables are created automatically on first run.

### Local Development Setup

**Option 1: PostgreSQL in Docker (Recommended)**

```bash
# Start PostgreSQL
docker run -d \
  --name quorum-postgres \
  -e POSTGRES_USER=quorum \
  -e POSTGRES_PASSWORD=quorum \
  -e POSTGRES_DB=quorum \
  -p 5432:5432 \
  postgres:15-alpine

# Start Redis (for rate limiting)
docker run -d \
  --name quorum-redis \
  -p 6379:6379 \
  redis:7-alpine

# Setup backend
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Setup frontend (new terminal)
cd frontend
npm install
npm start
```

**Frontend:** http://localhost:3000
**Backend API:** http://localhost:8000

---

## Features

### Core Functionality

- **Anonymous Voting**: Secure, hash-based vote tokens
- **QR Code Check-In**: Browser-generated QR codes for easy access
- **Real-Time Updates**: SSE connections for live vote counts
- **Admin Dashboard**: Create meetings, manage polls, view results
- **Idempotent Check-In**: Users can re-check-in safely if token is lost

### Technical Features

- **RESTful API**: Versioned endpoints under `/api/v1/`
- **JWT Authentication**: Stateless admin auth
- **Rate Limiting**: Prevent abuse (200 req/min default)
- **CORS Support**: Configurable origins
- **Health Checks**: `/health` endpoint for monitoring
- **Database Migrations**: Alembic for schema versioning

---

## Architecture

### Project Structure

```
quorum/
├── app/                      # Backend application
│   ├── main.py              # FastAPI app initialization
│   ├── api/                 # API layer
│   │   ├── deps.py          # Shared dependencies
│   │   └── v1/endpoints/    # Route handlers
│   ├── core/                # Configuration & security
│   ├── db/models/           # SQLAlchemy models
│   ├── schemas/             # Pydantic validation
│   └── services/            # Business logic
├── frontend/                # React SPA
│   └── src/
│       ├── App.jsx          # Main component
│       ├── api.js           # API client
│       └── components/      # React components
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # API integration tests
├── alembic/                # Database migrations
├── docker-compose.yml      # Development setup
├── docker-compose.production.yml  # Production setup
└── Dockerfile              # Multi-stage build
```

### Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- Redis (rate limiting)
- Alembic (migrations)
- Argon2 (password hashing)
- PyJWT (authentication)

**Frontend:**
- React 18
- React Router 6
- Vite (build tool)
- qrcode.react (QR generation)

**Testing:**
- pytest (backend, 45 tests, 82% coverage)
- Jest + React Testing Library (frontend, 91% coverage)

---

## Installation

### Docker Compose (Full Stack)

```bash
# Start all services
docker-compose up -d

# The stack includes:
# - PostgreSQL database
# - Redis cache
# - FastAPI + React app
```

### Manual Installation

**Backend:**

```bash
# Create virtual environment
python -m venv .venv
.venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Configure .env file
cp .env.example .env
# Edit .env with your settings

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend

# Install dependencies
npm install

# Development server (proxies to localhost:8000)
npm start

# Production build
npm run build
```

---

## Testing

### Backend Tests

```bash
# Activate virtual environment
.venv/Scripts/activate

# Run all tests
pytest

# With coverage report
pytest --cov=app

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only

# View HTML coverage report
# Opens: test-reports/backend/coverage-html/index.html
# Opens: test-reports/backend/test-report.html
```

**Test Structure:**
- Uses in-memory SQLite (no PostgreSQL needed)

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run once (CI mode)
npm test -- --watchAll=false

# With coverage
npm test -- --coverage --watchAll=false

# View reports
# Opens: test-reports/frontend/coverage/index.html
# Opens: test-reports/frontend/test-report/index.html
```

**Test Structure:**
- Uses Jest + React Testing Library
- MSW for API mocking

### Test Reports

All test artifacts are centralized in:

```
test-reports/
├── backend/
│   ├── test-report.html        # Test results
│   ├── coverage-html/          # Code coverage
│   ├── coverage.xml            # CI/CD format
│   └── coverage.json
└── frontend/
    ├── test-report/index.html  # Test results
    └── coverage/               # Code coverage
```

### Comprehensive Test Script

A comprehensive script (`run_all_tests.py`) sets up the environment and runs all tests. You can find information about it in `TEST_RUNNER_README.md`.

---

## Production Deployment

### Pre-Deployment Security Checklist

**CRITICAL**: Complete this checklist before deploying to production:

- [ ] **Change SECRET_KEY** - Generate cryptographically secure key:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] **Change ADMIN_PASSWORD** - Use strong password (minimum 12 characters) or hash it:
  ```bash
  python -c "from app.core.security import get_password_hash; print(get_password_hash('your-secure-password'))"
  ```
- [ ] **Set CORS_ORIGINS** - Specify exact domain(s), NOT `["*"]`:
  ```bash
  CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
  ```
- [ ] **Set ENVIRONMENT=production** - Enables security features (HTTPS-only cookies, etc.)
- [ ] **Enable HTTPS/TLS** - Required for secure cookies and data transmission
- [ ] **Configure Redis** - Required for distributed rate limiting in multi-instance deployments:
  ```bash
  REDIS_URL=redis://your-redis-host:6379
  ```
- [ ] **Verify rate limiting works** - Test with: `curl -I http://your-domain.com/health`
- [ ] **Review and rotate secrets** - Ensure no development keys in production
- [ ] **Run dependency security audit**:
  ```bash
  # Backend
  pip install pip-audit
  pip-audit

  # Frontend
  cd frontend && npm audit
  ```
- [ ] **Enable database backups** - Configure automated backups for PostgreSQL
- [ ] **Set up monitoring and alerting** - Monitor `/health` endpoint and error rates
- [ ] **Test admin login** - Verify authentication works with new credentials
- [ ] **Verify `.env` not in git** - Ensure `.env` is in `.gitignore` and not committed

### Environment Variables

**Required:**

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
ADMIN_PASSWORD=<your-secure-password>
CORS_ORIGINS=https://yourdomain.com
```

**Optional:**

```bash
REDIS_URL=redis://redis:6379  # For distributed rate limiting
TIMEZONE=America/New_York
ACCESS_TOKEN_EXPIRE_MINUTES=480
APP_TITLE=Quorum Voting System
```

### Quick Deploy with Docker

```bash
# Generate secure secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Build image
docker build -t quorum:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DATABASE_URL="postgresql://user:pass@host:5432/dbname" \
  -e SECRET_KEY="<your-generated-key>" \
  -e ADMIN_PASSWORD="<your-password>" \
  -e CORS_ORIGINS="https://yourdomain.com" \
  --name quorum \
  quorum:latest
```

### Using Docker Compose

```bash
# Use production compose file
docker-compose -f docker-compose.production.yml up -d

# Run migrations
docker-compose -f docker-compose.production.yml exec quorum alembic upgrade head

# View logs
docker-compose -f docker-compose.production.yml logs -f
```

### Platform-Specific Deployment

**Render:**
1. Create Web Service from GitHub repo
2. Add PostgreSQL database
3. Set environment variables in dashboard
4. Deploy automatically

**Railway:**
1. Create project from GitHub
2. Add PostgreSQL service
3. Set environment variables
4. Auto-deploys from Dockerfile

**Heroku:**
```bash
heroku create your-app
heroku addons:create heroku-postgresql:mini
heroku config:set ENVIRONMENT=production
heroku config:set SECRET_KEY="<key>"
heroku config:set ADMIN_PASSWORD="<password>"
git push heroku main
heroku run alembic upgrade head
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE-specific configuration
    location /api/v1/sse/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}
```

---

## Development

### Daily Workflow

**Start Services:**
```bash
# Terminal 1: Database
docker start quorum-postgres quorum-redis

# Terminal 2: Backend
.venv/Scripts/activate
uvicorn app.main:app --reload

# Terminal 3: Frontend
cd frontend
npm start
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin: http://localhost:3000/admin/login

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current version
alembic current
```

### Common Commands

```bash
# Backend
pytest                         # Run tests
pytest --cov=app              # With coverage
uvicorn app.main:app --reload # Dev server

# Frontend
npm start                     # Dev server
npm test                      # Run tests
npm run build                 # Production build

# Docker
docker-compose up -d          # Start all services
docker-compose down           # Stop all services
docker-compose logs -f api    # View backend logs
docker-compose restart        # Restart services
```

---

## Configuration

### Environment Variables Reference

Create a `.env` file based on `.env.example`. All environment variables with their defaults, implications, and security considerations:

#### Core Application Settings

| Variable | Default | Description | Performance Impact | Security Notes |
|----------|---------|-------------|-------------------|----------------|
| `ENVIRONMENT` | `development` | Application environment (`development` or `production`) | None | In production: enables HTTPS-only cookies, stricter validation |
| `APP_TITLE` | `Quorum Voting System` | Application title displayed in API docs | None | Display only, no security impact |
| `TIMEZONE` | `UTC` | Timezone for determining "current" meetings | None | Affects which meetings show as "available" |

#### Database Configuration

**Method 1: Connection URL (Recommended)**

| Variable | Example | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Full PostgreSQL connection string |

**Method 2: Individual Components**

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `quorum` | Database username |
| `POSTGRES_PASSWORD` | `quorum` | Database password |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `quorum` | Database name |

**Performance Tuning:**
- Connection pooling configured in `app/db/session.py`
- Default: `pool_size=15`, `max_overflow=25` (40 total connections)
- Adjust via code if needed for your workload

#### Security Settings

| Variable | Default | Description | Security Level | Notes |
|----------|---------|-------------|----------------|-------|
| `SECRET_KEY` | `dev-secret...` | JWT signing key | **CRITICAL** | Must be cryptographically random in production (32+ bytes) |
| `ADMIN_PASSWORD` | `adminpass` | Admin authentication password | **CRITICAL** | Can be plaintext or Argon2 hash (hash recommended) |
| `CORS_ORIGINS` | `["*"]` in dev | Allowed origins for CORS | **HIGH** | Must be specific domains in production, never `["*"]` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours) | JWT token lifetime | Medium | Shorter = more secure, longer = better UX |

**Security Recommendations:**
- **SECRET_KEY**: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **ADMIN_PASSWORD**: Hash with `python -c "from app.core.security import get_password_hash; print(get_password_hash('password'))"`
- **CORS_ORIGINS**: Set to exact domains: `https://yourdomain.com,https://www.yourdomain.com`

#### Rate Limiting & Caching

| Variable | Default | Description | Performance Impact | Scale Considerations |
|----------|---------|-------------|-------------------|---------------------|
| `REDIS_URL` | None (in-memory) | Redis connection for distributed rate limiting | Low | Required for multi-instance deployments |

**Without Redis:**
- Rate limiting works but is per-instance (not shared)
- Cache is in-memory (not shared across instances)
- Single-instance deployments work fine

**With Redis:**
- Rate limiting shared across all instances
- Better for load-balanced production deployments
- Example: `redis://redis-host:6379`

#### SSE & Real-Time Updates

Configured in `app/core/constants.py` (requires code change):

| Setting | Default | Description | Performance Impact |
|---------|---------|-------------|-------------------|
| `SSE_USER_INTERVAL` | `5` seconds | Update frequency for user SSE | Lower = more real-time, higher DB load |
| `SSE_ADMIN_INTERVAL` | `3` seconds | Update frequency for admin SSE | Lower = more real-time, higher DB load |

**Performance Trade-offs:**
- User interval: 5s = 200 users = ~40 queries/sec
- Admin interval: 3s = faster updates for admins watching votes
- Adjust based on concurrent user load and database capacity

#### Rate Limit Configuration

Configured in `app/core/rate_limit.py` (requires code change):

```python
RATE_LIMITS = {
    "check_in": "200/minute",           # Check-in endpoint
    "vote": "200/minute",               # Voting endpoint
    "available_meetings": "200/minute", # Meeting list
    "admin_read": "200/minute",         # Admin read operations
    "admin_write": "200/minute",        # Admin write operations
}
```

**When to Adjust:**
- Increase if legitimate users hit limits
- Decrease if seeing abuse or DDoS attempts
- Monitor `/health` endpoint for rate limit stats

### Example Configurations

**Development (`.env`):**
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql://quorum:quorum@localhost:5432/quorum
REDIS_URL=redis://localhost:6379
SECRET_KEY=dev-secret-key-change-in-production
ADMIN_PASSWORD=adminpass
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
TIMEZONE=America/New_York
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

**Production (`.env`):**
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://prod_user:$ecureP@ss@db.example.com:5432/quorum_prod
REDIS_URL=redis://redis.example.com:6379
SECRET_KEY=<32-byte-random-string-from-secrets.token_urlsafe>
ADMIN_PASSWORD=<argon2-hashed-password-or-very-strong-plaintext>
CORS_ORIGINS=https://voting.example.com,https://www.voting.example.com
TIMEZONE=America/New_York
ACCESS_TOKEN_EXPIRE_MINUTES=480
APP_TITLE=Quorum Voting System
```

### Customization

**Vote Options:**

Currently set to A-H (8 options). To change:

```python
# Backend: app/schemas/vote.py
vote: str = Field(..., pattern="^[A-J]$")  # A through J

# Frontend: frontend/src/components/VoteModal.jsx
const VOTE_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
```

**SSE Update Intervals:**

```python
# app/core/constants.py
SSE_USER_INTERVAL = 5    # seconds
SSE_ADMIN_INTERVAL = 3   # seconds
```

**Rate Limits:**

```python
# app/core/rate_limit.py
RATE_LIMITS = {
    "check_in": "200/minute",
    "vote": "200/minute",
    "available_meetings": "200/minute",
    "admin_read": "200/minute",
    "admin_write": "200/minute",
}
```

---

## Troubleshooting

### Common Issues

**"Can't check in" / "Invalid token"**
- Check browser console for errors
- Verify token exists: `localStorage.getItem('meeting_X_token')`
- Try re-checking in (idempotent - returns same token)
- Clear localStorage and check in fresh

**SSE connection fails**
- Check browser console for SSE errors
- Test endpoint: `curl http://localhost:8000/api/v1/sse/meetings?tokens=%7B%7D`
- Ensure reverse proxy doesn't buffer SSE (see nginx config)
- SSE auto-reconnects after 3 seconds on disconnect

**Database connection error**
- Check PostgreSQL is running: `docker ps | grep postgres`
- Verify DATABASE_URL is correct
- Test connection: `psql "postgresql://user:pass@host:5432/db"`

**Port already in use**
```bash
# Find process
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# Kill process
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # macOS/Linux
```

**Frontend build errors**
```bash
# Clean install
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Backend module errors**
```bash
# Recreate virtual environment
deactivate
rm -rf .venv
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```

### Debug Mode

**Backend:**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

**Frontend:**
```bash
# Enable React debug mode
REACT_APP_DEBUG=true npm start
```

---

## API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Public Endpoints:**
- `POST /api/v1/meetings/available` - Get available meetings
- `POST /api/v1/meetings/{id}/checkins` - Check in to meeting
- `POST /api/v1/meetings/{id}/polls/{poll_id}/votes` - Cast vote
- `GET /api/v1/sse/meetings` - SSE stream for updates

**Admin Endpoints:**
- `POST /api/v1/auth/admin/login` - Admin login
- `POST /api/v1/meetings` - Create meeting
- `POST /api/v1/meetings/{id}/polls` - Create poll
- `GET /api/v1/admin/meetings` - Get all meetings
- `DELETE /api/v1/admin/meetings/{id}` - Delete meeting
- `GET /api/v1/sse/admin/meetings` - SSE stream for admin

---

## Changelog

### Initial Release (2025)

**Features:**
- FastAPI backend with async capabilities
- Pure React SPA frontend
- Argon2-hashed vote tokens for security
- JWT-based admin authentication
- Server-Sent Events for real-time updates
- Client-side QR code generation
- Foreign key architecture (no duplicate token storage)

**Security Improvements:**
- Vote tokens stored as Argon2 hashes
- Idempotent check-in prevents "lost token" bug
- JWT authentication replaces session cookies
- Rate limiting on all endpoints

**Performance:**
- Async Python with FastAPI
- Bulk database queries
- SSE connections with auto-reconnect
- Client-side QR generation (zero server load)

**Bug Fixes:**
- Fixed "already checked in but can't vote" issue
- Tokens persist across refreshes (localStorage)
- Users can safely re-check-in with existing token

**Breaking Changes:**
- Database schema incompatible with v1.0
- API endpoints completely redesigned
- Authentication changed from sessions to JWT
- Requires migration for existing deployments

---

## License

MIT License - see LICENSE file for details

## Support

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Issues**: <your-repo>/issues

---

**Version**: 2.0.0
**Last Updated**: 2025
