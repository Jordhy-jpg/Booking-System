# Workroom Booking

An end-to-end coworking-space meeting-room booking system. It pairs a Vue single-page booking flow with a Django REST API and includes sample rooms, database migrations, authentication, and collision-safe reservations.

## Stack

- Backend: Python, Django, Django REST Framework, SimpleJWT, django-cors-headers
- Frontend: Vue 3 + Vite
- Database: SQLite by default for a zero-config evaluation run. The project already includes psycopg, so it can be pointed at PostgreSQL by changing `DATABASES` for deployment.

## Run locally

Prerequisites: Python 3.13+, [uv](https://docs.astral.sh/uv/), and Node.js 20+.

```bash
# terminal 1 - API
uv sync
cd booking_system
uv run python manage.py migrate
uv run python manage.py seed_booking_data
uv run python manage.py runserver
```

```bash
# terminal 2 - Vue app
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to Django during development. Direct browser access from the Vue server is also permitted by `CORS_ALLOWED_ORIGINS` in `booking_system/.env`.

## API

All routes work under `/api/` (for example, `/api/rooms`) and the three assessment routes also have root aliases (`/rooms`, `/slots`, `/bookings`). Successful responses are JSON; malformed inputs use a consistent `{ "error": { "code", "details" } }` shape.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/rooms` | List rooms: id, name, capacity, pricePerHour, facilities, image. |
| `GET` | `/api/slots?roomId=1&date=2026-10-20` | List a room's slots and date-specific `isAvailable` state. `date` is optional. |
| `POST` | `/api/bookings` | Create a booking. Returns `201` and its generated `code`. |
| `POST` | `/api/bookings/{code}/cancel` | Cancel your booking through three calendar days before its date (JWT required). |
| `POST` | `/api/auth/register/` | Register using Django's built-in `User` model. |
| `POST` | `/api/auth/token/` | Exchange username/password for JWT access and refresh tokens. |
| `POST` | `/api/auth/token/refresh/` | Refresh an access token. |
| `GET` | `/api/bookings/mine` | List the signed-in user's bookings (JWT required). |

Example booking request:

```json
{
  "roomId": 1,
  "slotId": 3,
  "date": "2026-10-20",
  "name": "Budi",
  "email": "budi@email.com",
  "phone": "081234567890",
  "participants": 3
}
```

### API behavior

- Invalid input returns `422` with field-level messages. A past date, mismatched room/slot, invalid email or phone, and a guest count above room capacity are rejected.
- An occupied room/slot/date combination returns `409`.
- The booking owner may cancel through the date three calendar days before the reservation. Cancellation on that cutoff date is allowed; after it, the API returns `409`. Cancelled reservations remain in booking history, but their time slot becomes available again.
- Missing resources naturally return `404`; successful reads return `200` and bookings return `201`.
- The booking write path uses an atomic transaction, row locking where supported, and a database uniqueness constraint. The database constraint is the final guard against simultaneous requests creating duplicate reservations.
- Writes to the room/slot catalogue require a Django staff user; public users may browse and place reservations.
- Signed-in users can see their own bookings. Reservations made while logged out remain guest reservations and are not attached to an account later.
- DRF throttles anonymous clients to 100 requests/hour, authenticated clients to 500/hour, and booking/registration endpoints to 15/hour.

## Data and testing

`seed_booking_data` is idempotent and creates three rooms with seven time slots each.

```bash
cd booking_system
uv run python manage.py test bookings
```

The included tests verify a successful reservation, capacity validation, duplicate-booking conflict handling, and the slot availability response.

## Assumptions

- A slot denotes a one-hour booking window and is unique within its room.
- Reservations are public by default, so a user can finish the required flow without an account; when a JWT is supplied, the booking is linked to that Django user.
- Prices are hourly Indonesian rupiah amounts. Payment and cancellation workflows are deliberately outside this test scope.

## Development assistance

This implementation was developed with AI assistance for project scaffolding, API and UI implementation, and test coverage, then verified through Django's test suite and system checks.
