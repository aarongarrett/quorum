import os
from pathlib import Path
import nox

# Reuse existing virtualenvs for faster runs
nox.options.reuse_existing_virtualenvs = True
# Default sessions when running "nox"
nox.options.sessions = ["lint", "unit", "e2e"]

# Common dependencies for test sessions
COMMON_DEPS = ["-rrequirements/dev.txt"]

# Environment variables to propagate
PASSED_ENV_VARS = [
    "QUORUM_FLASK_SECRET",
    "QUORUM_FLASK_ENV",
    "QUORUM_ADMIN_PASSWORD",
    "QUORUM_DATABASE_URL",
    "QUORUM_TIMEZONE",
]


def _set_env(session):
    """
    Propagate database and test-related environment variables into the session.
    Also ensure the project root is on PYTHONPATH.
    """
    # Ensure imports from the project root work
    session.env["PYTHONPATH"] = str(Path.cwd())
    for var in PASSED_ENV_VARS:
        if var in os.environ:
            session.env[var] = os.environ[var]


@nox.session(name="lint")
def lint(session):
    """
    Code formatting, linting, and type-checks:
      - isort
      - black
      - flake8
      - mypy
    """
    _set_env(session)
    session.install("isort", "black", "flake8", "mypy")
    session.run("isort", "app/", "tests/")
    session.run("black", "app/", "tests/")
    session.run("flake8", "app/", "tests/")
    session.run("mypy", "app/")


@nox.session(name="unit")
def unit(session):
    """
    Run unit tests against a real Postgres database.
    Pass positional args to target specific tests.
    Usage:
      nox -s unit             # runs all tests under tests/unit
      nox -s unit -- tests/unit/test_services.py::test_create_meeting
    """
    _set_env(session)
    session.install(*COMMON_DEPS)
    # Determine which tests to run: use posargs or default to whole unit suite
    tests = session.posargs or ["tests/unit"]
    # Reporting paths (relative)
    htmlcov_path = ".nox/htmlcov"
    session.run(
        "pytest",
        *tests,
        "--maxfail=1",
        "-vv",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:" + htmlcov_path,
        "--cov-report=xml",
        "--cov-fail-under=80",
    )


@nox.session(name="e2e")
def e2e(session):
    """
    Run end-to-end tests via pytest against the live Flask app.
    Pass positional args to target specific tests.
    Usage:
      nox -s e2e              # runs all tests under tests/e2e
      nox -s e2e -- tests/e2e/test_api.py::test_checkin_api
    """
    _set_env(session)
    session.install(*COMMON_DEPS)
    tests = session.posargs or ["tests/e2e"]
    session.run(
        "pytest",
        *tests,
        "--maxfail=1",
        "-vv",
        "--tb=short",
    )