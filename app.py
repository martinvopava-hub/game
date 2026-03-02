import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# Importujeme Blueprint a funkci pro registraci socketů z kostky.py
from kostky import kostky_bp, register_kostky_sockets, HTML_KOSTKY

app = Flask(__name__)
app.config['SECRET_KEY'] = 'herni-portal-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Registrujeme cesty pro kostky
app.register_blueprint(kostky_bp)

# Registrujeme logiku socketů pro kostky
register_kostky_sockets(socketio)

# --- MENU ---
@app.route('/')
def menu():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Herní Menu</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: white; text-align: center; padding: 50px; }
            .container { display: flex; justify-content: center; gap: 20px; margin-top: 50px; }
            .card { 
                background: #1a1a1a; border: 2px solid #444; border-radius: 15px; 
                padding: 30px; width: 200px; cursor: pointer; transition: 0.3s; 
                text-decoration: none; color: white;
            }
            .card:hover { border-color: #2ecc71; transform: scale(1.05); background: #222; }
            h1 { color: #f1c40f; }
        </style>
    </head>
    <body>
        <h1>Vyber si hru</h1>
        <div class="container">
            <a href="/kostky_hram" class="card">
                <h2>🎲 Kostky</h2>
                <p>Klasická hra v 10 000 bodů.</p>
            </a>
            <a href="/prsi" class="card">
                <h2>🃏 Prší</h2>
                <p>Oblíbená karetní hra.</p>
            </a>
        </div>
    </body>
    </html>
    """)

# Stránka pro kostky (volá se z blueprintu, ale pro jistotu ji definujeme i zde)
@app.route('/kostky_hram')
def kostky_page():
    return render_template_string(HTML_KOSTKY)

# Placeholder pro Prší
@app.route('/prsi')
def prsi():
    return "<h1>🃏 Prší</h1><p>Prší se právě připravuje...</p><a href='/'>Zpět do menu</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)