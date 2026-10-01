from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import time
import os
import sqlite3
import ssl
import socket
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import threading

app = Flask(__name__, static_folder=os.path.dirname(__file__), static_url_path='')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'history.db')

MONITORED_DOMAINS = [
    "lamongankab.go.id",
    "dprd.lamongankab.go.id",
    "diskominfo.lamongankab.go.id",
    "disdik.lamongankab.go.id",
    "dinkes.lamongankab.go.id",
    "bappeda.lamongankab.go.id",
    "rsud-soegiri.lamongankab.go.id",
    "dispendukcapil.lamongankab.go.id",
    "bpbd.lamongankab.go.id",
    "distan.lamongankab.go.id"
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS check_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time INTEGER,
            checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def auto_check_domain(domain):
    url = f"https://{domain}"
    try:
        start_time = time.time()
        resp = requests.get(url, timeout=10)
        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)
        status = 'UP'
    except:
        response_time_ms = None
        status = 'DOWN'
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO check_history (domain, status, response_time) VALUES (?, ?, ?)",
            (domain, status, response_time_ms)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Scheduler] DB error untuk {domain}: {e}")

def auto_check_all():
    print(f"[Scheduler] Mulai cek otomatis: {datetime.now().strftime('%H:%M:%S')}")
    threads = []
    for domain in MONITORED_DOMAINS:
        t = threading.Thread(target=auto_check_domain, args=(domain,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    print(f"[Scheduler] Selesai cek {len(MONITORED_DOMAINS)} domain")

init_db()

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    auto_check_all,
    'interval',
    minutes=30,
    id='auto_check_job',
    next_run_time=datetime.now()
)
scheduler.start()
print("[Scheduler] Background scheduler aktif - cek setiap 30 menit")

@app.route('/scheduler-status', methods=['GET'])
def scheduler_status():
    job = scheduler.get_job('auto_check_job')
    return jsonify({
        'status': 'aktif',
        'interval': '30 menit',
        'next_run': str(job.next_run_time) if job else None,
        'monitored_domains': len(MONITORED_DOMAINS)
    })

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/stats')
def stats():
    return send_from_directory(os.path.dirname(__file__), 'stats.html')

@app.route('/check', methods=['POST'])
def check():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'status': 'down', 'error': 'URL is required'}), 400
    if '://' not in url:
        domain = url.split('/')[0]
        url = 'https://' + url
    else:
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
    response_code = None
    response_time_ms = None
    error_msg = None
    try:
        start_time = time.time()
        resp = requests.get(url, timeout=10)
        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)
        response_code = resp.status_code
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO check_history (domain, status, response_time) VALUES (?, ?, ?)",
                      (domain, 'UP', response_time_ms))
            conn.commit()
            conn.close()
        except:
            pass
        return jsonify({
            'status': 'UP',
            'url': url,
            'status_code': response_code,
            'response_time': response_time_ms
        })
    except requests.exceptions.Timeout:
        error_msg = 'Request timeout after 10 seconds'
    except requests.exceptions.ConnectionError:
        error_msg = 'Connection error'
    except requests.exceptions.InvalidURL:
        error_msg = 'Invalid URL'
    except Exception as e:
        error_msg = str(e)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO check_history (domain, status, response_time) VALUES (?, ?, ?)",
                  (domain, 'DOWN', None))
        conn.commit()
        conn.close()
    except:
        pass
    return jsonify({
        'status': 'DOWN',
        'url': url,
        'status_code': response_code,
        'response_time': response_time_ms,
        'error': error_msg
    })

@app.route('/history', methods=['GET'])
def history():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': 'Domain required'}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT checked_at, status, response_time FROM check_history WHERE domain = ? ORDER BY id DESC LIMIT 48", (domain,))
        rows = c.fetchall()
        conn.close()
        result = [dict(row) for row in rows]
        result.reverse()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uptime', methods=['GET'])
def uptime():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': 'Domain required'}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        results = []
        for i in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            c.execute("SELECT status FROM check_history WHERE domain = ? AND date(checked_at) = ?", (domain, day))
            rows = c.fetchall()
            total_checks = len(rows)
            up_checks = sum(1 for r in rows if r[0] == 'UP')
            uptime_percent = round((up_checks / total_checks * 100), 2) if total_checks > 0 else 0
            results.append({'date': day, 'uptime_percent': uptime_percent, 'total_checks': total_checks})
        conn.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ssl', methods=['GET'])
def check_ssl():
    domain = request.args.get('domain', '')
    if not domain:
        return jsonify({'valid': False, 'error': 'Domain required'})
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
        expires_str = cert['notAfter']
        expires_at = datetime.strptime(expires_str, '%b %d %H:%M:%S %Y %Z')
        days_remaining = (expires_at - datetime.utcnow()).days
        issuer = dict(x[0] for x in cert.get('issuer', []))
        return jsonify({
            'valid': True,
            'expires_at': expires_at.strftime('%d %B %Y'),
            'days_remaining': days_remaining,
            'issuer': issuer.get('organizationName', 'Unknown')
        })
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/discover', methods=['POST'])
def discover():
    data = request.get_json() or {}
    domain = data.get('domain', 'lamongankab.go.id')
    parts = domain.split('.')
    is_specific = len(parts) > 3
    if is_specific:
        return jsonify({"subdomains": [domain], "total": 1, "mode": "specific"})
    try:
        resp = requests.get(
            f'https://crt.sh/?q=%.{domain}&output=json',
            timeout=15
        )
        if resp.status_code == 200:
            cert_data = resp.json()
            if isinstance(cert_data, list):
                crtsh_subdomains = set()
                for entry in cert_data:
                    name = entry.get('name_value', '')
                    for sub in name.split('\n'):
                        sub = sub.strip().lstrip('*.')
                        if domain in sub and sub:
                            crtsh_subdomains.add(sub)
                subdomains = sorted([s for s in crtsh_subdomains
                                     if s.endswith('.' + domain) or s == domain])
                if subdomains:
                    return jsonify({
                        'subdomains': subdomains,
                        'total': len(subdomains),
                        'source': 'crtsh'
                    })
    except Exception as e:
        print(f"[crt.sh] Error: {e}")
    return jsonify({
        'subdomains': [],
        'total': 0,
        'warning': 'Tidak dapat mengambil data subdomain'
    })

if __name__ == '__main__':
    app.run(debug=True)