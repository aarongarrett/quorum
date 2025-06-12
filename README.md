# Quorum - A Meeting and Voting Application

![Unit Tests](https://github.com/aarongarrett/quorum/actions/workflows/unit.yml/badge.svg)
![E2E Tests](https://github.com/aarongarrett/quorum/actions/workflows/e2e.yml/badge.svg)
![CI & CD](https://github.com/aarongarrett/quorum/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/codecov/c/github/aarongarrett/quorum.svg?branch=main)
![License](https://img.shields.io/github/license/aarongarrett/quorum)


## 1. Overview
Quorum is a web-based meeting and voting application built with Flask and PostgreSQL. It provides anonymous, QR-driven in-person voting for meetings. The application has functionality for managing meetings, conducting polls, and tracking participant check-ins, and it is containerized using Docker and follows modern development practices with comprehensive testing.

## 2. Core Features

### 2.1 Meeting Management
- Create and manage meetings with specific timeframes
- Generate unique meeting codes for participant access
- Track meeting attendance through check-ins
- Real-time metrics via SSE

### 2.2 Polling System
- Create multiple polls within a meeting
- Support for simple voting mechanisms with up to 8 choices per poll
- Track individual votes while maintaining voter anonymity

### 2.3 Check-in System
- QR code or unique meeting text code required for check-in
- Unique vote tokens for participants
- Timestamp tracking for attendance
- Meeting-specific check-in records


## 3. Quick Start

### 3.1 Prerequisites
- Python 3.10+
- Docker
- Chrome browser (for local development with Selenium)


### 3.2 Installation
```
git clone https://github.com/aarongarrett/quorum.git
cd quorum
pip install -r requirements/base.txt
docker-compose up -d
```

### 3.3 First poll in 5 minutes
1. Visit http://localhost:5000/admin
2. Log in (use "adminpass" if `ADMIN_PASSWORD` isn't set in the environment)
3. Create Meeting → copy meeting code
4. Create Poll
5. Visit http://localhost:5000
6. Check in for meeting with meeting code
7. Vote in the poll
8. Visit http://localhost:5000/admin to watch live results


## 4. Technical Details

### 4.1 Architecture Overview
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

### 4.2 Stack Architecture

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

## 5. Configuration
- **Environment Variables**
For development, these can be defined in a .env variable in the project root. See .example.env for an example. For production, these would need to be made available to the web container.
  - `QUORUM_FLASK_ENV`: Environment (development/testing/production)
  - `QUORUM_FLASK_SECRET`: Session security
  - `QUORUM_DATABASE_URL`: Database connection string
  - `QUORUM_ADMIN_PASSWORD`: Admin password
  - `QUORUM_TIMEZONE`: Timezone
- **Config classes**: DevelopmentConfig, TestingConfig, ProductionConfig in config.py

## 6. Project Structure

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

## 7. API Reference

All JSON & SSE endpoints live under `/api/*`. You can explore them interactively via Swagger UI at `GET /api/docs`, or grab the raw OpenAPI spec at `/api/swagger.json`.


### 7.1 Admin Authentication

```http
POST /api/login
Content-Type: application/json

{
  "password": "your-admin-password"
}
````

**Responses**

* **200 OK**

  ```json
  { "success": true }
  ```
* **400 Bad Request**

  ```json
  { "message": "Password is required" }
  ```
* **400 Bad Request**

  ```json
  { "message": "Invalid password" }
  ```


### 7.2 Create Meeting (Admin Only)

```http
POST /api/admin/meetings
Content-Type: application/json
Cookie: session=…

{
  "start_time": "2025-06-20T15:00:00",
  "end_time":   "2025-06-20T17:00:00"
}
```

**Responses**

* **201 Created**

  ```json
  {
    "meeting_id": 42,
    "meeting_code": "ABCD1234"
  }
  ```
* **403 Forbidden**

  ```json
  { "message": "Unauthorized" }
  ```
* **500 Internal Server Error**

  ```json
  { "message": "Detailed error message" }
  ```


### 7.3 Create Poll (Admin Only)

```http
POST /api/admin/meetings/{meeting_id}/polls
Content-Type: application/json
Cookie: session=…

{
  "name": "Best Flavor"
}
```

**Responses**

* **201 Created**

  ```json
  { "poll_id": 7 }
  ```
* **403 Forbidden**

  ```json
  { "message": "Unauthorized" }
  ```
* **400 Bad Request**

  ```json
  { "message": "Name must not be empty" }
  ```
* **500 Internal Server Error**

  ```json
  { "message": "Detailed error message" }
  ```


### 7.4 List & Filter Meetings

#### GET meetings (public)

```http
GET /api/meetings
```

Uses cookies & session tokens to filter which meetings you’ve checked in to.

#### POST meetings (API-only)

```http
POST /api/meetings
Content-Type: application/json

{
  "42": "token-for-meeting-42",
  "99": "token-for-meeting-99"
}
```

**Response** `200 OK`

```json
[
  {
    "id": 42,
    "meeting_code": "ABCD1234",
    "start_time": "2025-06-20T15:00:00Z",
    "end_time": "2025-06-20T17:00:00Z",
    "checked_in": true,
    "polls": [ … ]
  },
  …
]
```


### 7.5 Check‐In

```http
POST /api/meetings/{meeting_id}/checkins
Content-Type: application/json

{ "meeting_code": "ABCD1234" }
```

**Responses**

* **200 OK**

  ```json
  { "token": "vote-token-xyz" }
  ```
* **400 Bad Request**

  ```json
  { "message": "Meeting code must not be empty" }
  ```
* **404 Not Found**

  ```json
  { "message": "Invalid meeting code" }
  ```
* **500 Internal Server Error**


### 7.6 Vote

```http
POST /api/meetings/{meeting_id}/polls/{poll_id}/votes
Content-Type: application/json

{
  "token": "vote-token-xyz",
  "vote":  "A"
}
```

**Responses**

* **200 OK**

  ```json
  { "success": true }
  ```
* **400 Bad Request**

  ```json
  { "message": "Token must not be empty" }
  ```
* **404 Not Found**

  ```json
  { "message": "You have already voted" }
  ```
* **500 Internal Server Error**


### 7.7 Server-Sent Events (SSE)

#### Public Stream

```http
GET /api/meetings/stream
Accept: text/event-stream
```

Yields an updated list of available meetings every 5 seconds.

#### Admin Metrics Stream

```http
GET /api/admin/meetings/stream
Accept: text/event-stream
Cookie: session=…  # must be admin
```

Yields real-time check-in counts and vote tallies every 3 seconds.





## 8. Route Reference

| Endpoint                   | Methods       | Rule                                                         |
|----------------------------|---------------|--------------------------------------------------------------|
| `admin.admin_redirect`     | `GET`         | `/admin/`                                                    |
| `admin.dashboard_ui`       | `GET`         | `/admin/dashboard`                                           |
| `admin.generate_qr`        | `GET`         | `/admin/meetings/<int:meeting_id>/qr.<fmt>`                  |
| `admin.login_ui`           | `GET, POST`   | `/admin/login`                                               |
| `admin.logout_ui`          | `POST`        | `/admin/logout`                                              |
| `admin.meeting_create_ui`  | `GET, POST`   | `/admin/meetings`                                            |
| `admin.meeting_delete_ui`  | `DELETE, POST`| `/admin/meetings/<int:meeting_id>`                           |
| `admin.poll_create_ui`     | `GET, POST`   | `/admin/meetings/<int:meeting_id>/polls`                     |
| `admin.poll_delete_ui`     | `DELETE, POST`| `/admin/meetings/<int:meeting_id>/polls/<int:poll_id>`       |
| `api.api_admin_login`      | `POST`        | `/api/login`                                                 |
| `api.api_admin_stream`     | `GET`         | `/api/admin/meetings/stream`                                 |
| `api.api_checkin_api`      | `POST`        | `/api/meetings/<int:meeting_id>/checkins`                    |
| `api.api_create_meeting`   | `POST`        | `/api/admin/meetings`                                        |
| `api.api_create_poll`      | `POST`        | `/api/admin/meetings/<int:meeting_id>/polls`                 |
| `api.api_meetings`         | `GET, POST`   | `/api/meetings`                                              |
| `api.api_user_stream`      | `GET`         | `/api/meetings/stream`                                       |
| `api.api_vote_api`         | `POST`        | `/api/meetings/<int:meeting_id>/polls/<int:poll_id>/votes`   |
| `api.doc`                  | `GET`         | `/api/docs`                                                  |
| `api.root`                 | `GET`         | `/api/`                                                      |
| `api.specs`                | `GET`         | `/api/swagger.json`                                          |
| `public.auto_checkin`      | `GET`         | `/meetings/<int:meeting_id>/auto_checkin`                    |
| `public.checkin_ui`        | `GET, POST`   | `/meetings/<int:meeting_id>/checkins`                        |
| `public.home_ui`           | `GET`         | `/`                                                          |
| `public.vote_ui`           | `GET, POST`   | `/meetings/<int:meeting_id>/polls/<int:poll_id>/votes`       |
| `restx_doc.static`         | `GET`         | `/swaggerui/<path:filename>`                                 |
| `static`                   | `GET`         | `/static/<path:filename>`                                    |


## 9. Development Workflow

### 9.1 Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Chrome browser (for local Selenium testing)

### 9.2 Getting Started
1. Clone the repository
2. Copy `.example.env` to `.env` and configure environment variables
3. Start the development environment: `docker-compose up -d`
4. Run database migrations: `docker-compose exec web flask db upgrade`
5. Access the application at http://localhost:5000

### 9.3 Testing
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

### 9.4 Development Server
1. Configure development environment variables in `.env`
2. Build and start containers: `docker-compose up -d --build`
3. Database migrations are carried out automatically in entrypoint.sh

## 10. Deployment
1. Create the Postgres database and note its URL
2. Configure production environment variables (particularly QUORUM_DATABASE_URL)
3. Build the web container: `docker build -f Dockerfile.web .`
4. Database migrations are carried out automatically in entrypoint.sh


## 11. Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests as needed
5. Run the test suite
6. Submit a pull request

## 12. License
MIT License

## 13. Contact
Aaron Garrett [<aaron.lee.garrett@gmail.com>]
