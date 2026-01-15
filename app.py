from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, redirect, g
from psycopg2 import pool, OperationalError, IntegrityError
import hashlib
import base64
import os

app = Flask(__name__)

try:
    db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dbname=os.environ.get('DB_NAME', 'urlshortener'),
            user=os.environ.get('DB_USER', 'url_user'),
            password=os.environ['DB_PASSWORD'],
            host=os.environ.get('DB_HOST', 'localhost')
    )
except (OperationalError, KeyError) as e:
    print(f"Failed to initialize database pool: {e}")
    raise

def get_db():
    if 'db' not in g:
        try:
            g.db = db_pool.getconn()
        except OperationalError:
            return None
    return g.db

@app.teardown_appcontext
def close_db(_) -> None: 
    db = g.pop('db', None)
    if db is not None:
        db_pool.putconn(db)


def hash_url(url: str) -> str:
    hash_bytes = hashlib.sha256(url.encode()).digest()
    #Take first 6 bytes, base64 encode, remove padding
    short_hash = base64.urlsafe_b64encode(hash_bytes[:6]).decode().rstrip('=')
    return short_hash

def validate_url(url:str) -> bool:
    """Basic URL validation"""
    return url.startswith(('http://', 'https://')) and len(url) < 2048

@app.route('/shorten', methods=['POST'])
def shorten():
    try:
        data = request.get_json()

        if not data or not data.get('url'):
            return jsonify({'error': 'URL is required'}), 400

        url = data.get('url')
        if not validate_url(url):
            return jsonify({'error':'Invalid URL format'}), 400

        code = hash_url(url)
        
        db = get_db()
        if not db:
            return jsonify({'error':'Database connection failed'}), 503
        
        with get_db().cursor() as cursor:

            # Check if URL already exists
            cursor.execute(
                "SELECT short_code FROM urls WHERE original_url = %s",
                (url,)
            )
            existing = cursor.fetchone()

            if existing:
                return jsonify({'short_code': existing[0]})
            try:
            # Insert new
                cursor.execute(
                    "INSERT INTO urls (original_url, short_code) VALUES (%s, %s)",
                    (url, code)
                )
                db.commit()
            
            except IntegrityError:
                db.rollback()
                return jsonify({'error': 'Short code collision'}), 500

            return jsonify({'short_code' : code})
    
    except Exception as e:
        app.logger.error(f"Error in shorten endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/<short_code>')
def redirect_url(short_code: str):
    try:
        if len(short_code) > 10:
            return jsonify({'error': 'Invalid short code'}), 400

        db = get_db()
        if not db: 
            return jsonify({'error': 'Database connection failed'}), 503

        with get_db().cursor() as cursor:
            cursor.execute(
                "SELECT id, original_url FROM urls WHERE short_code = %s",
                (short_code,)
            )
            result = cursor.fetchone()
    
            if result:
                url_id, original_url = result

                #Log Click
                ip = request.remote_addr
                ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
                referrer = request.referrer
                user_agent = request.headers.get('User-Agent')

                try:
                    cursor.execute(
                        "INSERT INTO clicks (url_id, ip_hash, referrer, user_agent) VALUES (%s, %s, %s, %s)",
                        (url_id, ip_hash, referrer, user_agent)
                    )
                    db.commit()
                except Exception as e:
                    app.logger.error(f"Failed to log click {e}")
                    #Continue redirect even if logging fails

                return redirect(original_url)

            return jsonify({'error': 'Not found'}), 404
        
    except Exception as e:
        app.logger.error(f"Error in redirect endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/stats/<short_code>')
def stats(short_code: str):
    try:
        if len(short_code) > 10:
            return jsonify({'error': 'Invalid short code'}), 400

        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 503

        with get_db().cursor() as cursor:

            #Get URL info
            cursor.execute(
                    "SELECT id, original_url, created_at FROM urls WHERE short_code = %s", 
                    (short_code,)
            )
            url_data = cursor.fetchone()

            if not url_data:
                return jsonify({'error': 'Not found'}), 404
    
            url_id, original_url, created_at = url_data

            # Get total clicks
            cursor.execute(
                    "SELECT COUNT(*) FROM clicks WHERE url_id = %s",
                    (url_id,)
            )
            total_clicks = (cursor.fetchone() or [0])[0]

            #Get recent clicks with details
            cursor.execute(
                    "SELECT clicked_at, referrer, user_agent FROM clicks WHERE url_id = %s ORDER BY clicked_at DESC LIMIT 10",
                    (url_id,)
            )
            recent_clicks = cursor.fetchall()

            return jsonify ({
                'short_code': short_code,
                'original_url': original_url,
                'created_at': str(created_at),
                'total_clicks': total_clicks,
                'recent_clicks': [
                    {
                        'timestamp': str(click[0]),
                        'referrer': click[1],
                        'user_agent': click[2]
                    } for click in recent_clicks
                ]
            })

    except Exception as e:
        app.logger.error(f"Error in stats endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
