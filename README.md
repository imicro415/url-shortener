# URL Shortener

A Flask-based URL shortening service with click tracking and analytics.


## Live Demo
https://url-shortener-wurd.onrender.com

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

## Example Usage
Shorten a URL:
```bash
curl -X POST -H "Content-Type: application/json" \
 -d '{"url":"https://example.com"}' \
 https://url-shortener-wurd.onrender.com/shorten
```

Redirect:
```bash
curl -I https://url-shortener-wurd.onrender.com/abc123
```

View statistics:
```bash
curl https://url-shortener-wurd.onrender.com/stats/abc123

```
## API Endpoints

### Shorten URL 
```
POST /shorten
Content-Type: application/json

Body: {"url":"https://example.com"}
Response: {"short_code": "abc123"}
```

### Redirect
```
GET /{short_code}
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

## Database Schema
```sql
CREATE TABLE urls (
    id SERIAL PRIMARY KEY,
    original_url TEXT NOT NULL,
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

## Notes 
- Free tier may experience cold starts (~30s initial load)
- Deterministic hashing means same URL always gets same short code

