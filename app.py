import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# ############################################################
# ZMĚNA: Importujeme i Blueprint a registraci pro hru PRŠÍ
# ############################################################
from kostky import kostky_bp, register_kostky_sockets
try:
    from prsi import prsi_bp, register_prsi_sockets
except ImportError:
    print("Soubor prsi.py nebyl nalezen!")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'portal-2026-multi-game'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- REGISTRACE KOSTEK ---
app.register_blueprint(kostky_bp)
register_kostky_sockets(socketio)

# ############################################################
# ZMĚNA: Registrace nové hry PRŠÍ do systému Flasku a Socketů
# ############################################################
try:
    app.register_blueprint(prsi_bp)
    register_prsi_sockets(socketio)
except NameError:
    pass

# --- MENU ŠABLONA ---
HTML_MENU = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Herní Portál</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: white; text-align: center; padding-top: 80px; }
        .container { display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; padding: 20px; }
        .card {
            background: #161616; border: 2px solid #333; border-radius: 20px;
            padding: 40px; width: 250px; text-decoration: none; color: white;
            transition: all 0.3s ease; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .card:hover {
            border-color: #2ecc71; transform: translateY(-10px);
            background: #1c1c1c; box-shadow: 0 15px 40px rgba(46, 204, 113, 0.2);
        }
        .icon { font-size: 60px; margin-bottom: 20px; }
        h1 { font-size: 3.5em; color: #f1c40f; margin-bottom: 50px; }
        .badge { display: inline-block; padding: 5px 12px; background: #2ecc71; border-radius: 50px; font-size: 10px; font-weight: bold; margin-top: 15px; }
    </style>
</head>
<body>
    <h1>HERNÍ PORTÁL</h1>
    <div class="container">
        <a href="/kostky_hram" class="card">
            <div class="icon">🎲</div>
            <h2>KOSTKY</h2>
            <p>Klasická hra o 10 000 bodů.</p>
            <div class="badge">AKTIVNÍ</div>
        </a>

        <a href="/prsi_hram" class="card">
            <div class="icon">🃏</div>
            <h2>PRŠÍ</h2>
            <p>Karetní bitva pro 2-4 hráče.</p>
            <div class="badge">AKTIVNÍ</div>
        </a>
    </div>
</body>
</html>
"""

@app.route('/')
def main_menu():
    return render_template_string(HTML_MENU)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Portál běží na portu {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)