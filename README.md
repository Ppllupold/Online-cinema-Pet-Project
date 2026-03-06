# 🎬 Online Cinema — Backend API

A RESTful backend for an online cinema platform built with FastAPI. Supports user authentication, movie catalog browsing, shopping cart, order management, and Stripe-based payments.

---

## Tech Stack

- **Python 3.12** + **FastAPI**
- **PostgreSQL** — primary database
- **SQLAlchemy 2.0** (async) + **Alembic** — ORM and migrations
- **Stripe** — payment processing
- **SendGrid** — transactional emails
- **Docker** + **Docker Compose** — containerization
- **Poetry** — dependency management
- **pytest** + **pytest-asyncio** — testing

---

## Features

- JWT authentication (access + refresh tokens)
- Account activation and password reset via email
- Movie catalog with filtering, sorting, and pagination
- Genre, actor, and director management
- Shopping cart
- Order placement and cancellation
- Stripe Checkout integration with webhook handling
- Swagger UI documentation

---

## Running with Docker

### 1. Clone the repository

```bash
git clone https://github.com/your-username/online-cinema-pet-project.git
cd online-cinema-pet-project
```

### 2. Create a `.env` file

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Required variables (see [Environment Variables](#environment-variables) below).

### 3. Start all services

```bash
docker-compose up --build
```

The API will be available at: `http://localhost:8000`

---

## Running Locally (without Docker)

### 1. Install dependencies

```bash
poetry install
```

### 2. Start PostgreSQL

Make sure a PostgreSQL instance is running and matches the credentials in your `.env`.

```bash
docker-compose up postgres
```

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn src.main:app --reload
```

---

## Running Tests

Tests use a separate PostgreSQL container (`cinema_postgres_test`). Make sure it is running:

```bash
docker-compose up postgres_test
```

Then run:

```bash
pytest src/tests
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `POSTGRES_HOST` | Database host |
| `POSTGRES_PORT` | Database port |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `JWT_SECRET_KEY` | Secret key for JWT signing |
| `JWT_ALGORITHM` | JWT algorithm (e.g. `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL in days |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Sender email address |

---

## API Documentation

Once the server is running, interactive Swagger UI is available at:

```
http://localhost:8000/docs
```

### Endpoints overview

| Tag | Prefix | Description |
|---|---|---|
| Accounts | `/api/v1/accounts` | Registration, activation, login, tokens, password management |
| Movies | `/api/v1/movies` | Movie catalog with filters and pagination |
| Genres | `/api/v1/genres` | Genre CRUD |
| Stars | `/api/v1/stars` | Actor CRUD |
| Shopping Cart | `/api/v1/cart` | Cart management |
| Orders | `/api/v1/orders` | Order placement and cancellation |
| Payments | `/api/v1/payments` | Stripe Checkout initiation and payment history |
| Webhooks | `/api/v1/webhooks` | Stripe webhook event handling |