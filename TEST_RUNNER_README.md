# Test Runner Guide

## Quick Start

Run all tests:
```bash
python run_all_tests.py
```

The script handles everything automatically - no need to manually create venvs or install dependencies!

## Options

```bash
# Skip specific test suites
python run_all_tests.py --skip-backend   # Skip backend (pytest) tests
python run_all_tests.py --skip-frontend  # Skip frontend (Jest) tests
python run_all_tests.py --skip-e2e       # Skip E2E (Playwright) tests

# Keep servers running after tests (useful for debugging)
python run_all_tests.py --keep-running

# Keep virtual environment (speeds up subsequent runs)
python run_all_tests.py --keep-venv

# Combine options
python run_all_tests.py --skip-e2e --keep-running --keep-venv
```

## What It Does

The script automatically:

1. ✓ Checks prerequisites (Docker, Python, Node.js)
2. ✓ Creates virtual environment (`.venv-test`)
3. ✓ Installs Python dependencies from `requirements-dev.txt`
4. ✓ Starts PostgreSQL via Docker Compose
5. ✓ Runs database migrations (Alembic)
6. ✓ Starts backend server on http://localhost:8000
7. ✓ Starts frontend dev server on http://localhost:3000
8. ✓ Installs frontend dependencies (if needed)
9. ✓ Runs backend tests (pytest with coverage)
10. ✓ Runs frontend tests (Jest with coverage)
11. ✓ Runs E2E tests (Playwright)
12. ✓ Cleans up all processes, Docker containers, and venv

## Prerequisites

**Only these are required - the script handles the rest:**

- **Docker Desktop** - Must be running before executing the script
- **Python 3.8+** - No packages need to be installed globally
- **Node.js 16+** - With npm

## Test Reports

After running, test reports are available at:

- **Backend coverage**: `test-reports/backend/coverage-html/index.html`
- **Backend test report**: `test-reports/backend/test-report.html`
- **Frontend coverage**: `frontend/coverage/lcov-report/index.html`
- **E2E report**: `test-reports/playwright/index.html`

## Performance Tips

### Speed up subsequent test runs

Use `--keep-venv` to avoid recreating the virtual environment:
```bash
python run_all_tests.py --keep-venv
```

The `.venv-test` directory will be reused on the next run, saving ~30 seconds.

To manually clean up the venv:
```bash
# Windows
rmdir /s .venv-test

# macOS/Linux
rm -rf .venv-test
```

## Troubleshooting

### "Docker is not running"
Start Docker Desktop before running the script.

### "Failed to create virtual environment"
Ensure you have Python 3.8+ with `venv` module:
```bash
python --version
python -m venv --help
```

### "Failed to install backend dependencies"
Check your internet connection and that `requirements-dev.txt` exists.

### "Backend server failed to start"
- Check if port 8000 is already in use
- Ensure PostgreSQL is running (`docker-compose ps`)
- Check database connection: `psql postgresql://quorum:quorum@localhost:5432/quorum`

### "Frontend server failed to start"
- Check if port 3000 is already in use
- Try deleting `frontend/node_modules` and re-running

### "Playwright browsers not installed"
The script will auto-install Chromium on first E2E test run. If it fails:
```bash
cd frontend
npx playwright install chromium
```

### Cleanup hung processes

If servers don't stop cleanly:

**Windows:**
```bash
taskkill /F /IM python.exe
taskkill /F /IM node.exe
docker-compose down
rmdir /s .venv-test
```

**macOS/Linux:**
```bash
pkill -f uvicorn
pkill -f "npm run dev"
docker-compose down
rm -rf .venv-test
```

## Manual Testing Workflow

If you want to run tests manually with servers already running:

1. Start services:
   ```bash
   docker-compose up -d db
   alembic upgrade head
   uvicorn app.main:app --reload
   # In another terminal:
   cd frontend && npm run dev
   ```

2. Run tests individually:
   ```bash
   pytest                        # Backend tests
   cd frontend && npm test       # Frontend tests
   cd frontend && npm run test:e2e  # E2E tests
   ```

3. Stop services:
   ```bash
   docker-compose down
   # Ctrl+C to stop uvicorn and Vite
   ```

## CI/CD Integration

For continuous integration, you can use:

```bash
# Exit with non-zero code if any tests fail
python run_all_tests.py

# Skip E2E in quick CI pipelines
python run_all_tests.py --skip-e2e
```

The script exits with code 0 (success) or 1 (failure), making it suitable for CI/CD pipelines.
