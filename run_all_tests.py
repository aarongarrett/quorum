#!/usr/bin/env python3
"""
Quorum - All Tests Runner

This script runs all tests (backend, frontend, and e2e) with proper setup and teardown.
It automatically creates a virtual environment, installs dependencies, and cleans up.

Usage:
    python run_all_tests.py                 # Run all tests
    python run_all_tests.py --skip-backend  # Skip backend tests
    python run_all_tests.py --skip-frontend # Skip frontend tests
    python run_all_tests.py --skip-e2e      # Skip E2E tests
    python run_all_tests.py --keep-running  # Don't stop servers after tests
    python run_all_tests.py --keep-venv     # Don't delete venv after tests
"""

import argparse
import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# ANSI color codes
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Track processes and resources for cleanup
backend_process = None
frontend_process = None
tests_failed = False
venv_created = False
venv_path = None

def print_step(message):
    """Print a step header."""
    print(f"\n{Colors.CYAN}{'=' * 55}")
    print(f"  {message}")
    print(f"{'=' * 55}{Colors.RESET}\n")

def print_success(message):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message):
    """Print an info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")

def run_command(cmd, cwd=None, check=True, capture_output=False, env=None, shell=False):
    """Run a command and return the result."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=True,
                text=True,
                env=env or os.environ.copy(),
                shell=shell
            )
            return result
        else:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                env=env or os.environ.copy(),
                shell=shell
            )
            return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e

def check_command_exists(command):
    """Check if a command exists in PATH."""
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["where", command],
                check=True,
                capture_output=True
            )
        else:
            subprocess.run(
                ["which", command],
                check=True,
                capture_output=True
            )
        return True
    except subprocess.CalledProcessError:
        return False

def wait_for_url(url, max_attempts=30, delay=1):
    """Wait for a URL to become available."""
    import urllib.request
    import urllib.error

    for attempt in range(max_attempts):
        try:
            response = urllib.request.urlopen(url, timeout=1)
            if response.status == 200:
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass

        print(".", end="", flush=True)
        time.sleep(delay)

    print()  # New line after dots
    return False

def get_venv_executable(venv_path, executable):
    """Get the path to an executable in the virtual environment."""
    if platform.system() == "Windows":
        if executable == "python":
            return venv_path / "Scripts" / "python.exe"
        else:
            return venv_path / "Scripts" / f"{executable}.exe"
    else:
        return venv_path / "bin" / executable

def create_venv(project_root):
    """Create virtual environment and install dependencies."""
    global venv_created, venv_path

    venv_path = project_root / ".venv-test"

    # Check if venv already exists
    if venv_path.exists():
        print_info(f"Virtual environment already exists at {venv_path}")
        return venv_path

    print_step("Creating virtual environment...")

    # Create venv
    result = run_command(
        [sys.executable, "-m", "venv", str(venv_path)],
        cwd=project_root,
        check=False
    )
    if result.returncode != 0:
        print_error("Failed to create virtual environment")
        return None

    venv_created = True
    print_success(f"Virtual environment created at {venv_path}")

    # Upgrade pip
    print_info("Upgrading pip...")
    venv_python = get_venv_executable(venv_path, "python")
    run_command(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=project_root,
        check=False,
        capture_output=True
    )

    # Install backend dependencies
    print_info("Installing backend dependencies...")
    requirements_dev = project_root / "requirements-dev.txt"
    if not requirements_dev.exists():
        print_error(f"requirements-dev.txt not found at {requirements_dev}")
        return None

    result = run_command(
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements_dev)],
        cwd=project_root,
        check=False
    )
    if result.returncode != 0:
        print_error("Failed to install backend dependencies")
        return None

    print_success("Backend dependencies installed")

    return venv_path

def cleanup(keep_venv=False):
    """Stop all running processes and clean up resources."""
    global backend_process, frontend_process, venv_created, venv_path

    print_step("Cleaning up processes...")

    # Stop backend process
    if backend_process and backend_process.poll() is None:
        print_info(f"Stopping backend server (PID: {backend_process.pid})...")
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(backend_process.pid)],
                             capture_output=True)
            else:
                backend_process.terminate()
                try:
                    backend_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    backend_process.kill()
            print_success("Backend server stopped")
        except Exception as e:
            print_error(f"Error stopping backend: {e}")

    # Stop frontend process
    if frontend_process and frontend_process.poll() is None:
        print_info(f"Stopping frontend server (PID: {frontend_process.pid})...")
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)],
                             capture_output=True)
            else:
                frontend_process.terminate()
                try:
                    frontend_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    frontend_process.kill()
            print_success("Frontend server stopped")
        except Exception as e:
            print_error(f"Error stopping frontend: {e}")

    # Stop Docker Compose
    print_info("Stopping Docker Compose services...")
    try:
        subprocess.run(
            ["docker-compose", "down"],
            capture_output=True,
            check=False
        )
        print_success("Docker Compose stopped")
    except Exception as e:
        print_error(f"Error stopping Docker Compose: {e}")

    # Clean up virtual environment
    if venv_created and venv_path and venv_path.exists() and not keep_venv:
        print_info(f"Removing virtual environment at {venv_path}...")
        try:
            shutil.rmtree(venv_path)
            print_success("Virtual environment removed")
        except Exception as e:
            print_error(f"Error removing venv: {e}")
    elif keep_venv and venv_path:
        print_info(f"Keeping virtual environment at {venv_path}")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
    cleanup(keep_venv=False)
    sys.exit(1)

def main():
    global backend_process, frontend_process, tests_failed, venv_path

    # Parse arguments
    parser = argparse.ArgumentParser(description="Run all Quorum tests")
    parser.add_argument("--skip-backend", action="store_true", help="Skip backend tests")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend tests")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip E2E tests")
    parser.add_argument("--keep-running", action="store_true", help="Keep servers running after tests")
    parser.add_argument("--keep-venv", action="store_true", help="Keep virtual environment after tests")
    args = parser.parse_args()

    # Register cleanup handlers
    atexit.register(lambda: cleanup(keep_venv=args.keep_venv) if not args.keep_running else None)
    signal.signal(signal.SIGINT, signal_handler)
    if platform.system() != "Windows":
        signal.signal(signal.SIGTERM, signal_handler)

    start_time = time.time()

    # Print banner
    print(f"""
{Colors.MAGENTA}{Colors.BOLD}
╔═══════════════════════════════════════════════════╗
║                                                   ║
║             QUORUM - ALL TESTS RUNNER             ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
{Colors.RESET}
""")

    # Check prerequisites
    print_step("Checking prerequisites...")

    # Check Docker
    if not check_command_exists("docker"):
        print_error("Docker is not installed or not in PATH")
        return 1

    result = run_command(["docker", "info"], capture_output=True, check=False)
    if result.returncode != 0:
        print_error("Docker is not running. Please start Docker.")
        return 1
    print_success("Docker is running")

    # Check Python
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_success(f"Python found: {python_version}")

    # Check Node
    if not check_command_exists("node"):
        print_error("Node.js is not installed or not in PATH")
        return 1
    result = run_command(["node", "--version"], capture_output=True)
    print_success(f"Node.js found: {result.stdout.strip()}")

    # Check npm
    if not check_command_exists("npm"):
        print_error("npm is not installed or not in PATH")
        return 1

    # Get project root
    project_root = Path(__file__).parent.absolute()

    # Create virtual environment and install dependencies
    venv_path = create_venv(project_root)
    if not venv_path:
        print_error("Failed to set up virtual environment")
        return 1

    # Get paths to venv executables
    venv_python = get_venv_executable(venv_path, "python")
    venv_alembic = get_venv_executable(venv_path, "alembic")
    venv_uvicorn = get_venv_executable(venv_path, "uvicorn")
    venv_pytest = get_venv_executable(venv_path, "pytest")

    # Start PostgreSQL
    print_step("Starting PostgreSQL via Docker Compose...")
    result = run_command(
        ["docker-compose", "up", "-d", "db"],
        cwd=project_root,
        check=False
    )
    if result.returncode != 0:
        print_error("Failed to start PostgreSQL")
        return 1
    print_success("PostgreSQL container started")

    # Wait for PostgreSQL to be healthy
    print_info("Waiting for PostgreSQL to be healthy...")
    max_wait = 60  # seconds
    elapsed = 0
    while elapsed < max_wait:
        result = run_command(
            ["docker", "exec", "quorum-dev-db-1", "pg_isready", "-U", "quorum"],
            capture_output=True,
            check=False
        )
        if result.returncode == 0:
            break
        print(".", end="", flush=True)
        time.sleep(2)
        elapsed += 2

    if elapsed >= max_wait:
        print()
        print_error("PostgreSQL failed to become healthy")
        return 1

    print()
    print_success("PostgreSQL is healthy")

    # Run database migrations
    print_step("Running database migrations...")
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://quorum:quorum@localhost:5432/quorum"

    result = run_command(
        [str(venv_alembic), "upgrade", "head"],
        cwd=project_root,
        env=env,
        check=False
    )
    if result.returncode != 0:
        print_error("Database migrations failed")
        return 1
    print_success("Database migrations completed")

    # Start backend server
    print_step("Starting backend server...")
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://quorum:quorum@localhost:5432/quorum"
    env["SECRET_KEY"] = "test-secret-key-for-testing-only"
    #env["ADMIN_PASSWORD"] = "adminpass"  # pulls from .env file instead

    # Start uvicorn using venv
    backend_process = subprocess.Popen(
        [str(venv_uvicorn), "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=project_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait for backend to be ready
    print_info("Waiting for backend server to be ready...")
    if not wait_for_url("http://localhost:8000/health", max_attempts=30, delay=1):
        print_error("Backend server failed to start")
        return 1
    print_success("Backend server is ready")

    # Start frontend server
    print_step("Starting frontend server...")
    frontend_dir = project_root / "frontend"

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print_info("Installing frontend dependencies...")
        if platform.system() == "Windows":
            result = run_command("npm install", cwd=frontend_dir, check=False, shell=True)
        else:
            result = run_command(["npm", "install"], cwd=frontend_dir, check=False)
        if result.returncode != 0:
            print_error("Failed to install frontend dependencies")
            return 1

    # Start Vite dev server
    # On Windows, npm is a .cmd file, so we need shell=True
    if platform.system() == "Windows":
        frontend_process = subprocess.Popen(
            "npm run dev",
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
    else:
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    # Wait for frontend to be ready
    print_info("Waiting for frontend server to be ready...")
    if not wait_for_url("http://localhost:3000", max_attempts=30, delay=1):
        print_error("Frontend server failed to start")
        return 1
    print_success("Frontend server is ready")

    # Run backend tests
    if not args.skip_backend:
        print_step("Running backend tests (pytest)...")
        result = run_command([str(venv_pytest)], cwd=project_root, check=False)
        if result.returncode != 0:
            print_error("Backend tests failed")
            tests_failed = True
        else:
            print_success("Backend tests passed")
    else:
        print_info("Skipping backend tests")

    # Run frontend tests
    if not args.skip_frontend:
        print_step("Running frontend tests (Jest)...")
        if platform.system() == "Windows":
            result = run_command("npm test", cwd=frontend_dir, check=False, shell=True)
        else:
            result = run_command(["npm", "test"], cwd=frontend_dir, check=False)
        if result.returncode != 0:
            print_error("Frontend tests failed")
            tests_failed = True
        else:
            print_success("Frontend tests passed")
    else:
        print_info("Skipping frontend tests")

    # Run E2E tests
    if not args.skip_e2e:
        print_step("Running E2E tests (Playwright)...")

        # Check if Playwright browsers are installed
        playwright_dir = Path.home() / ".cache" / "ms-playwright"
        if platform.system() == "Windows":
            playwright_dir = Path.home() / "AppData" / "Local" / "ms-playwright"

        if not playwright_dir.exists():
            print_info("Installing Playwright browsers...")
            if platform.system() == "Windows":
                run_command("npx playwright install chromium", cwd=frontend_dir, shell=True)
            else:
                run_command(["npx", "playwright", "install", "chromium"], cwd=frontend_dir)

        if platform.system() == "Windows":
            result = run_command("npm run test:e2e", cwd=frontend_dir, check=False, shell=True)
        else:
            result = run_command(["npm", "run", "test:e2e"], cwd=frontend_dir, check=False)
        if result.returncode != 0:
            print_error("E2E tests failed")
            tests_failed = True
        else:
            print_success("E2E tests passed")
    else:
        print_info("Skipping E2E tests")

    # Summary
    end_time = time.time()
    duration = int(end_time - start_time)
    minutes = duration // 60
    seconds = duration % 60

    print(f"""

{Colors.CYAN}╔═══════════════════════════════════════════════════╗
║                                                   ║
║                  TEST SUMMARY                     ║
║                                                   ║
╚═══════════════════════════════════════════════════╝{Colors.RESET}
""")

    if tests_failed:
        print(f"  {Colors.RED}Status: FAILED{Colors.RESET}")
        print(f"  Duration: {minutes}m {seconds}s")
        print(f"\n  {Colors.YELLOW}Some tests failed. Check output above for details.{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}Status: PASSED{Colors.RESET}")
        print(f"  Duration: {minutes}m {seconds}s")
        print(f"\n  {Colors.GREEN}All tests passed successfully! ✓{Colors.RESET}")

    print(f"\n  {Colors.CYAN}Test reports available in:{Colors.RESET}")
    print(f"    - Backend: test-reports/backend/")
    print(f"    - Frontend: frontend/coverage/")
    print(f"    - E2E: test-reports/playwright/")
    print()

    if args.keep_running:
        print_info("Keeping servers running (press Ctrl+C to stop)")
        print_info("  Backend: http://localhost:8000")
        print_info("  Frontend: http://localhost:3000")
        print_info("  API docs: http://localhost:8000/docs")
        print_info("  To stop manually, run: docker-compose down")
        if args.keep_venv:
            print_info(f"  Virtual environment: {venv_path}")
        print()

        # Keep script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Stopping servers...{Colors.RESET}")
            cleanup(keep_venv=args.keep_venv)

    return 1 if tests_failed else 0

if __name__ == "__main__":
    sys.exit(main())
