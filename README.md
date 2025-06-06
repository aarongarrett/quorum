# Quorum Web Application

A Flask-based web application with PostgreSQL database, using Docker for containerization and deployment. The application includes comprehensive testing with Tox, including unit tests and end-to-end tests with Selenium.

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Chrome browser (for local development with Selenium)

## Project Structure

- `app/` - Main application package
  - `blueprints/` - Flask blueprints for different components
  - `models/` - SQLAlchemy models
  - `templates/` - HTML templates
  - `services/` - Business logic
  - `static/` - Static files (CSS, JS, images)
  - `__init__.py` - Application factory
  - `config.py`
  - `database.py`
  - `models.py`
  - `utils.py`
- `migrations/` - Database migration files (Flask-Migrate)
- `tests/` - Test files
  - `e2e/` - End-to-end tests
  - `unit/` - Unit tests
- `docker-compose.yml` - Production Docker configuration
- `docker-compose.test.yml` - Test environment Docker configuration
- `Dockerfile` - Application Docker image configuration
- `alembic.ini`
- `docker-compose.yml`
- `docker-compose.test.yml`
- `mypy.ini`
- `requirements-dev.txt`
- `requirements.txt`
- `run.py`
- `tox.ini` - Test configuration

## Getting Started

### Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd quorum
   ```

2. Create a `.env` file in the project root with the necessary environment variables:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   DATABASE_URL=postgresql://postgres:pgadminpwd@db:5432/quorum_dev
   ```

3. Start the development environment:
   ```bash
   docker-compose up -d
   ```

4. The application will be available at http://localhost:5000

## Database Management

### Initializing the Database

To create the initial database tables:

```bash
docker-compose exec web flask db upgrade
```

### Creating Migrations

After making changes to your models, create a new migration:

```bash
docker-compose exec web flask db migrate -m "Your migration message"
```

### Applying Migrations

Apply pending migrations:

```bash
docker-compose exec web flask db upgrade
```

## Testing

### Running Tests

The test environment includes Selenium for end-to-end testing. To run the tests:

1. Start the test environment:
   ```bash
   .\test_docker_up.bat
   ```

2. Open a shell in the tox container:
   ```bash
   docker exec -it quorum-tox-1 bash
   ```

3. Run the tests using tox (also includes coverage):
   ```bash
   tox
   ```
   
   Or run specific test types:
   ```bash
   tox -e lint    # Run linter
   tox -e unit    # Run unit tests
   tox -e e2e     # Run end-to-end tests
   ```

4. When finished, clean up the test environment:
   ```bash
   .\test_docker_down.bat
   ```

## Deployment

### Production Deployment

1. Ensure your production environment variables are set in `.env`
2. Build and start the production containers:
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```
3. Run database migrations:
   ```bash
   docker-compose exec web flask db upgrade
   ```

The application will be available at http://localhost:5000

## Environment Variables

- `FLASK_APP` - Entry point of the application (default: `run.py`)
- `FLASK_ENV` - Environment (development, testing, production)
- `SECRET_KEY` - Secret key for session management
- `DATABASE_URL` - Database connection URL
- `BASE_URL` - Base URL for the application (used in testing)
- `SELENIUM_REMOTE_URL` - Selenium WebDriver URL (used in testing)

## Troubleshooting

- If you encounter database connection issues, ensure the PostgreSQL container is running and healthy
- For test failures, check the logs of the selenium container for browser-related issues
- Use `docker-compose logs` to view application logs

