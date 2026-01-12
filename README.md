# URL Shortener

A Flask-based URL shortening service with click tracking and analytics.

## Features 

- Deterministic URL shortening using SHA-256 hashing
- Click tracking with IP hashing, referrer, and user agent logging
- Analytics endpoint for viewing click statistics
- PostgreSQL database with connection pooling

## Tech Stack 

- Python 3.x
- Flask
- PostgreSQL
- psycopg2
- Deployed on Render

### Shorten URL 
```
POST /shorten
Content-Type: application/json

Body: {"url":"https://example.com"}
Response: {"short_code": "abc123"}
```

### Redirect
```
Get /{short_code}
Response: 302 redirect to original URL
```

### Statistics
```
GET /stats/{short_code}
Response: JSON with click count and recent click details
```

### Local Setup
1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create PostgreSQL database and tables (see schema below)
4. Create `.env` file with database credentials
5. Run: `python app.py`

## Database schema
```sql
CREATE TABLE urls (
    id SERIAL PRIMARY KEY,
    originl_url TEXT NOT NULL,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clicks (
    id SERIAL PRIMARY KEY,
    url_id INTEGER REFERENCES urls(id),
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_hash VARCHAR(64),
    referrer TEXT,
    user_agent TEXT
);
```

## Live Demo
https://url-shortener-wurd.onrender.com
