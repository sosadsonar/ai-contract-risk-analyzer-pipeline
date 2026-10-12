# Backend

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- PyMuPDF

## Run locally

### Create virtual environment

python -m venv .venv

### Install dependencies

pip install -r requirements.txt

### Run server

uvicorn app.main:app --reload

### Swagger

http://localhost:8000/docs