# Installation

This guide covers all aspects of installing DBWarden, from basic installation to advanced configurations.

## Prerequisites

- Python 3.10 or higher
- pip or poetry for package management
- Access to a target database (PostgreSQL, MySQL, or SQLite)

## Basic Installation

### Using pip

```bash
pip install dbwarden
```

### Using poetry

```bash
poetry add dbwarden
```

## Database-Specific Installations

DBWarden supports multiple databases. Install the dependencies for your specific database:

### PostgreSQL (Synchronous)

```bash
pip install dbwarden psycopg2-binary
```

### PostgreSQL (Asynchronous)

```bash
pip install dbwarden asyncpg
```

### MySQL (Synchronous)

```bash
pip install dbwarden mysql-connector-python
```

### SQLite (Synchronous)

SQLite support is included by default with SQLAlchemy.

### SQLite (Asynchronous)

```bash
pip install dbwarden aiosqlite
```

## Complete Development Installation

Install all dependencies including development tools:

```bash
pip install dbwarden[dev]
```

Or with poetry:

```bash
poetry add --group dev dbwarden
```

## Verifying Installation

Verify that DBWarden is installed correctly:

```bash
dbwarden version
```

You should see output similar to:

```
DBWarden Version: 1.0.0
Python Version: 3.12.7 (main, Jan 19 2026, 23:31:25) [GCC 15.2.1 20251112]
```

## Installation from Source

For development or to get the latest features:

```bash
git clone https://github.com/emiliano-gandini-outeda/dbwarden.git
cd dbwarden
pip install -e .
```

## Virtual Environment Setup

It is recommended to install DBWarden in a virtual environment:

### Using venv

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
pip install dbwarden
```

### Using poetry

```bash
poetry install
poetry shell
```

## Docker Integration

DBWarden can be used within Docker containers:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install dbwarden

CMD ["dbwarden", "--help"]
```

### Docker Compose Example

```yaml
services:
  app:
    build: .
    volumes:
      - .:/app
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Note: Create a `warden.toml` file for DBWarden configuration instead of using `.env` for database settings.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 512 MB | 1 GB+ |
| Disk | 100 MB | 500 MB+ |
| Database | PostgreSQL 12+ | PostgreSQL 15+ |

## Troubleshooting

### Command Not Found

If `dbwarden` command is not found after installation:

1. Ensure your virtual environment is activated
2. Check if pip installed the package correctly:

```bash
pip show dbwarden
```

3. Add the Python scripts directory to your PATH:

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows
setx PATH "%PATH%;%APPDATA%\Python\PythonXX\Scripts"
```

### Import Errors

If you encounter import errors:

```bash
pip install --upgrade pip
pip install --upgrade dbwarden
```

### Database Driver Issues

Ensure you have the correct database driver installed:

```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install mysql-connector-python

# SQLite (included)
# No additional driver needed
```

## Upgrading

To upgrade DBWarden to the latest version:

```bash
pip install --upgrade dbwarden
```

Or with poetry:

```bash
poetry update dbwarden
```
