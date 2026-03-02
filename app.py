import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# Importujeme Blueprint a funkci pro registraci socketů z tvého souboru kostky.py
try:
    from kostky import kostky_bp, register_kostky_sockets
except ImportError:
    print("CHYBA: Soubor kostky.py nebyl nalezen ve stejné složce!")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'herni-portal-2026-top-secret'

# SocketIO musí být definován zde, aby ho mohly využívat všechny hry
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Registrujeme cesty (URL) pro kostky
app.register_blueprint(kostky_bp)

# Registrujeme logiku socketů (ovládání hry) pro kostky
register_kostky_sockets(socketio)

# --- MENU ŠABLONA ---
HTML_MENU = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Herní Portál</title>
    <style>
        body { 
            font-family: 'Segoe UI', sans-serif; 
            background: #0a0a0a; 
            color: white; 
            text-align: center; 
            margin: 0; 
            padding-top: 80px; 
        }
        .container {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            padding: 20px;
        }
        .card {
            background: #161616;
            border: 2px solid #333;
            border-radius: 20px;
            padding: 40px;
            width: 250px;
            text-decoration: none;
            color: white;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .card:hover {
            border-color: #2ecc71;
            transform: translateY(-10px);
            background: #1c1c1c;
            box-shadow: 0 15px 40px rgba(46, 204, 113, 0.2);
        }
        .icon { font-size: 60px; margin-bottom: 20px; }
        h1 { font-size: 3.5em; color: #f1c40f; margin-bottom: 50px; text-shadow: 0 0 20px rgba(241, 196, 15, 0.3); }
        h2 { margin: 10px 0; letter-spacing: 2px; }
        p { color: #888; font-size: 0.9em; }
        .badge {
            display: inline-block;
            padding: 5px 12px;
            background: #2ecc71;
            border-radius: 50px;
            font-size: 10px;
            font-weight: bold;
            margin-top: 15px;
        }
        .locked { opacity: 0.5; cursor: not-allowed; border-style: dashed; }
        .locked:hover { transform: none; border-color: #333; background: #161616; }
    </style>
</head>
<body>

    <h1>HERNÍ PORTÁL</h1>

    <div class="container">
        <a href="/kostky_hram" class="card">
            <div class="icon">🎲</div>
            <h2>KOSTKY</h2>
            <p>Klasická hra o 10 000 bodů. Vyžaduje štěstí i taktiku.</p>
            <div class="badge">AKTIVNÍ</div>
        </a>

        <a href="#" class="card locked">
            <div class="icon">🃏</div>
            <h2>PRŠÍ</h2>
            <p>Oblíbená karetní hra. Už brzy na tvém monitoru!</p>
            <div style="background:#555" class="badge">PŘIPRAVUJEME</div>
        </a>
    </div>

</body>
</html>
"""

@app.route('/')
def main_menu():
    return render_template_string(HTML_MENU)

if __name__ == '__main__':
    # Spuštění celého portálu
    port = int(os.environ.get("PORT", 5000))
    print(f"Server běží na portu {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)