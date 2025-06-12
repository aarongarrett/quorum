# Quorum - Project Information

## Overview
Quorum is a web-based meeting and voting application built with Flask and PostgreSQL. It provides functionality for managing meetings, conducting polls, and tracking participant check-ins. The application is containerized using Docker and follows modern development practices with comprehensive testing.

## Core Features

### Meeting Management
- Create and manage meetings with specific timeframes
- Generate unique meeting codes for participant access
- Track meeting attendance through check-ins

### Polling System
- Create multiple polls within a meeting
- Support for simple voting mechanisms
- Track individual votes while maintaining voter anonymity

### Check-in System
- Unique vote tokens for participants
- Timestamp tracking for attendance
- Meeting-specific check-in records

## Technical Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Flask-Migrate (Alembic)
- **API**: RESTful endpoints for frontend communication

### Frontend
- Templating: Jinja2
- Static assets served through Flask

### Development & Deployment
- **Containerization**: Docker and Docker Compose
- **Testing**: Pytest with unit and end-to-end tests
- **CI/CD**: GitHub Actions for automated testing
- **Code Quality**: Mypy for type checking, Flake8 for linting

## Project Structure

```
quorum/
├── app/                    # Main application package
│   ├── blueprints/         # Flask blueprints for modular organization
│   │   ├── admin/          # Admin interface routes
│   │   ├── api/            # API endpoints
│   │   └── public/         # Public-facing routes
│   ├── services/           # Business logic
│   ├── static/             # Static files (CSS, JS, images)
│   ├── templates/          # HTML templates
│   ├── __init__.py         # Application factory
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database initialization
│   ├── models.py           # Database models
│   └── utils.py            # Utility functions
├── migrations/             # Database migration files
├── tests/                  # Test suite
│   ├── e2e/                # End-to-end tests
│   └── unit/               # Unit tests
├── .env                    # Environment variables
├── docker-compose.yml      # Main Docker Compose configuration
├── Dockerfile.web          # Web application Dockerfile
├── requirements/           # Python dependencies
├── tox.ini                 # Test configuration
└── run.py                  # Application entry point
```

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
Run the full test suite using Tox:
```bash
tox
```

Or run specific test types:
```bash
tox -e lint    # Run linter
tox -e unit    # Run unit tests
tox -e e2e     # Run end-to-end tests
```

### Database Management
- Create migrations: `docker-compose exec web flask db migrate -m "description"`
- Apply migrations: `docker-compose exec web flask db upgrade`

## Deployment

### Production
1. Configure production environment variables in `.env`
2. Build and start containers: `docker-compose -f docker-compose.yml up -d --build`
3. Apply database migrations

### Environment Variables
- `FLASK_APP`: Application entry point
- `FLASK_ENV`: Environment (development/testing/production)
- `SECRET_KEY`: Session security
- `DATABASE_URL`: Database connection string
- `BASE_URL`: Application base URL

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests as needed
5. Run the test suite
6. Submit a pull request

## License
[Specify License]

## Contact
[Your Contact Information]
