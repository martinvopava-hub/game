import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# Importujeme Blueprint a funkci pro registraci socketů z druhého souboru
from kostky import kostky_bp, register_kostky_sockets

app = Flask(__name__)
app.config['SECRET_KEY'] = 'portal-tajne-heslo-2026'
# Důležité: SocketIO musí být definován v hlavním app.py
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Registrujeme Blueprint (tím se zprovozní adresa /kostky_hram)
app.register_blueprint(kostky_bp)

# Registrujeme události SocketIO pro kostky
register_kostky_sockets(socketio)

@app.route('/')
def menu():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Herní Portál</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: white; text-align: center; padding-top: 100px; }
            .menu-container { display: flex; justify-content: center; gap: 30px; }
            .game-card { 
                background: #1a1a1a; border: 2px solid #444; border-radius: 20px; 
                padding: 40px; width: 220px; text-decoration: none; color: white; 
                transition: 0.4s; box-shadow: 0 10px 20px rgba(0,0,0,0.5);
            }
            .game-card:hover { border-color: #2ecc71; transform: translateY(-10px); background: #222; }
            h1 { font-size: 3em; margin-bottom: 50px; color: #f1c40f; }
            .status { font-size: 0.8em; color: #888; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>HERNÍ PORTÁL</h1>
        <div class="menu-container">
            <a href="/kostky_hram" class="game-card">
                <div style="font-size: 50px;">🎲</div>
                <h2>KOSTKY</h2>
                <p>Hra o 10 000 bodů</p>
                <div class="status">Online: Aktivní</div>
            </a>
            
            <a href="#" class="game-card" style="opacity: 0.5; cursor: not-allowed;">
                <div style="font-size: 50px;">🃏</div>
                <h2>PRŠÍ</h2>
                <p>Karetní klasika</p>
                <div class="status">Připravujeme...</div>
            </a>
        </div>
    </body>
    </html>
    """)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)