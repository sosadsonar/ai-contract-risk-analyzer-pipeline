# Backend Architecture v0.1

## Architecture

Layered Modular Architecture

API
↓
Service
↓
Repository
↓
PostgreSQL

AI integrations:
- Clause AI
- Risk AI
- Explanation AI

## Backend Responsibilities

- Document upload
- Document parsing
- Pipeline orchestration
- Storage
- API
- AI integration

## W1 Scope

- FastAPI skeleton
- PDF upload
- PDF text extraction
- PostgreSQL setup
- Contract persistence

## Diagram

Frontend
   │
   ▼
FastAPI
   │
   ▼
Analysis Service
   │
   ├──── Clause AI
   ├──── Risk AI
   └──── Explanation AI
   │
   ▼
Repository
   │
   ▼
PostgreSQL