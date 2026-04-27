# project-name

> Short project description

## Requirements

- Python 3.14+
- [Poetry](https://python-poetry.org/)

## Installation

```bash
# Clone the repo
git clone https://github.com/wginc/project-name.git
cd project-name

# Install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
```

Open `.env` and fill in any required values before running the project.

## Running Locally

```bash
poetry env activate
```

## Running Tests

```bash
poetry run pytest
```

## Development

```bash
# Check formatting
poetry run black --check .

# Lint
poetry run ruff check .

# Format in place
poetry run black .
```

## Project Structure

```
project-name/
├── .github/
│   └── workflows/
│       └── ci.yml        # CI — runs Black, Ruff, and pytest on every push and PR
├── project_name/
│   └── __init__.py
├── tests/
│   └── test_main.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Branching

We follow the Innovations team branching strategy. Day-to-day work branches off `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```
