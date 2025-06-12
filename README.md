# Quorum - A Meeting and Voting Application
[![CI & CD](https://github.com/aarongarrett/quorum/actions/workflows/ci.yml/badge.svg)](https://github.com/aarongarrett/quorum/actions/workflows/ci.yml)


## Overview
Quorum is a web-based meeting and voting application built with Flask and PostgreSQL. It provides anonymous, QR-driven in-person voting for meetings. The application has functionality for managing meetings, conducting polls, and tracking participant check-ins, and it is containerized using Docker and follows modern development practices with comprehensive testing.

## Core Features

### Meeting Management
- Create and manage meetings with specific timeframes
- Generate unique meeting codes for participant access
- Track meeting attendance through check-ins
- Real-time metrics via SSE

### Polling System
- Create multiple polls within a meeting
- Support for simple voting mechanisms with up to 8 choices per poll
- Track individual votes while maintaining voter anonymity

### Check-in System
- QR code or unique meeting text code required for check-in
- Unique vote tokens for participants
- Timestamp tracking for attendance
- Meeting-specific check-in records


## Quick Start

### Prerequisites
- Python 3.10+
- Docker
- Chrome browser (for local development with Selenium)


### Installation
```
git clone https://github.com/aarongarrett/quorum.git
cd quorum
pip install -r requirements/base.txt
docker-compose up -d
```

### First poll in 5 minutes
1. Visit http://localhost:5000/admin
2. Log in (use "adminpass" if `ADMIN_PASSWORD` isn't set in the environment)
3. Create Meeting → copy meeting code
4. Create Poll
5. Visit http://localhost:5000
6. Check in for meeting with meeting code
7. Vote in the poll
8. Visit http://localhost:5000/admin to watch live results


## Technical Details

### Architecture Overview
#### Factory Pattern
  - **create_app(config_name)** → Flask app + config + DB + blueprints

#### Blueprints
  - **public_bp**: public UI (home, check-in, vote)
  - **admin_bp**: admin UI (login, dashboard, CRUD)
  - **api_bp**: JSON/SSE endpoints

#### Service Layer
  - **Thin controllers**: all business logic lives in services/

#### Database
  - **SQLAlchemy models**: Meeting, Poll, Checkin, PollVote; Cascading deletes, indexed for performance

#### Real-time
  - **SSE streams**: public (/api/meetings/stream) and admin (/api/admin/meetings/stream)

### Stack Architecture

#### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Flask-Migrate (Alembic)
- **API**: RESTful endpoints for frontend communication

#### Frontend
- **Templating**: Jinja2
- **Static assets**: served through Flask

#### Development & Deployment
- **Containerization**: Docker and Docker Compose
- **Testing**: Pytest with unit and end-to-end tests
- **CI/CD**: GitHub Actions for automated testing
- **Code Quality**: Mypy for type checking, Flake8 for linting

## Configuration
- **Environment Variables**
For development, these can be defined in a .env variable in the project root. See .example.env for an example. For production, these would need to be made available to the web container.
  - `QUORUM_FLASK_ENV`: Environment (development/testing/production)
  - `QUORUM_FLASK_SECRET`: Session security
  - `QUORUM_DATABASE_URL`: Database connection string
  - `QUORUM_ADMIN_PASSWORD`: Admin password
  - `QUORUM_TIMEZONE`: Timezone
- **Config classes**: DevelopmentConfig, TestingConfig, ProductionConfig in config.py

## Project Structure

```
quorum/
├── app/                        # Main application package
│   ├── blueprints/             # Flask blueprints for modular organization
│   │   ├── admin/              # Admin interface routes
│   │   ├── api/                # API endpoints
│   │   └── public/             # Public-facing routes
│   ├── services/               # Business logic
│   ├── static/                 # Static files (CSS, JS, images)
│   ├── templates/              # HTML templates
│   ├── __init__.py             # Application factory
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database initialization
│   ├── models.py               # Database models
│   └── utils.py                # Utility functions
├── migrations/                 # Database migration files
├── tests/                      # Test suite
│   ├── e2e/                    # End-to-end tests
│   └── unit/                   # Unit tests
├── .env                        # Environment variables
├── docker-compose.stress.yml   # Docker Compose configuration for stress testing
├── Dockerfile.locust           # Locust stress testing Dockerfile
├── docker-compose.e2e.yml      # Docker Compose configuration for E2E testing
├── docker-compose.yml          # Main Docker Compose configuration
├── Dockerfile.web              # Web application Dockerfile
├── entrypoint.sh               # Production application entry point
├── gunicorn.conf.py            # Configuration for gunicorn
├── locustfile.py               # Configuration for Locust (stress testing)
├── noxfile.py                  # Test configuration
├── requirements/               # Python dependencies
├── run.py                      # Development application entry point
└── setup.cfg                   # Linter configuration
```

## API Reference

- Admin Authentication

- Create Meeting

- Create Poll

- TO DO HERE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


## Development Workflow

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Chrome browser (for local Selenium testing)

### Getting Started
1. Clone the repository
2. Copy `.example.env` to `.env` and configure environment variables
3. Start the development environment: `docker-compose up -d`
4. Run database migrations: `docker-compose exec web flask db upgrade`
5. Access the application at http://localhost:5000

### Testing
#### Overview
- **Lint**: isort + black + mypy + flake8
- **Unit tests**: pytest + testcontainers
- **End-to-end tests**: pytest + Selenium

#### Instructions
Run the full test suite using Nox:
```bash
nox
```

Or run specific test types:
```bash
nox -s lint    # Run linter
nox -s unit    # Run unit tests
nox -s e2e     # Run end-to-end tests
```

### Development Server
1. Configure development environment variables in `.env`
2. Build and start containers: `docker-compose up -d --build`
3. Database migrations are carried out automatically in entrypoint.sh

## Deployment

### Production Server
1. Create the Postgres database and note its URL
1. Configure production environment variables (particularly QUORUM_DATABASE_URL)
2. Build the web container: `docker build -f Dockerfile.web .`
3. Database migrations are carried out automatically in entrypoint.sh


## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests as needed
5. Run the test suite
6. Submit a pull request

## License
MIT License

## Contact
Aaron Garrett [<aaron.lee.garrett@gmail.com>]
