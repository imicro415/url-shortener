from flask import Flask, request, jsonify, redirect, g
from psycopg2 import pool
from dotenv import load_dotenv
import hashlib
import base64
import os

load_dotenv()

app = Flask(__name__)

db_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dbname=os.environ.get('DB_NAME', 'urlshortener'),
        user=os.environ.get('DB_USER', 'url_user'),
        password=os.environ['DB_PASSWORD'],
        host=os.environ.get('DB_HOST', 'localhost')
        )

def get_db():
    if 'db' not in g:
        g.db = db_pool.getconn()
    return g.db

@app.teardown_appcontext
def close_db(_): 
    db = g.pop('db', None)
    if db is not None:
        db_pool.putconn(db)


def hash_url(url):
    hash_bytes = hashlib.sha256(url.encode()).digest()
    #Take first 6 bytes, base64 encode, remove padding
    short_hash = base64.urlsafe_b64encode(hash_bytes[:6]).decode().rstrip('=')
    return short_hash

@app.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()

    if not data or not data.get('url'):
        return jsonify({'error': 'URL is required'}), 400

    url = data.get('url')
    code = hash_url(url)
    
    with get_db().cursor() as cursor:

    # Check if URL already exists
        cursor.execute(
            "SELECT short_code FROM urls WHERE original_url = %s",
            (url,))
        existing = cursor.fetchone()

        if existing:
            return jsonify({'short_code': existing[0]})
    
    # Insert new
        cursor.execute(
            "INSERT INTO urls (original_url, short_code) VALUES (%s, %s)",
            (url, code)
        )
        get_db().commit()    
        return jsonify({'short_code' : code})

@app.route('/<short_code>')
def redirect_url(short_code):
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

            cursor.execute(
                    "INSERT INTO clicks (url_id, ip_hash, referrer, user_agent) VALUES (%s, %s, %s, %s)",
                    (url_id, ip_hash, referrer, user_agent)
            )
            get_db().commit()
            return redirect(original_url)

        return jsonify({'error': 'Not found'}), 404

@app.route('/stats/<short_code>')
def stats(short_code):
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
        cursor.execute("SELECT COUNT(*) FROM clicks WHERE url_id = %s",
                    (url_id,))
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

if __name__ == '__main__':
    app.run(debug=True)
