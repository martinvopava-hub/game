import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO

# Importujeme Blueprint a funkci pro sockety z druhého souboru
from kostky import kostky_bp, register_sockets

app = Flask(__name__)
app.config['SECRET_KEY'] = 'portal-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Registrace Blueprintu (cest k webovým stránkám)
app.register_blueprint(kostky_bp)

# Registrace SocketIO událostí pro kostky
register_sockets(socketio)

@app.route('/')
def menu():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Herní Menu</title>
        <style>
            body { font-family: sans-serif; background: #0f0f0f; color: white; text-align: center; padding-top: 100px; }
            .btn-game { 
                display: inline-block; padding: 40px; margin: 20px; 
                background: #1a1a1a; border: 2px solid #444; border-radius: 15px;
                text-decoration: none; color: white; transition: 0.3s; width: 200px;
            }
            .btn-game:hover { border-color: #2ecc71; transform: scale(1.05); }
        </style>
    </head>
    <body>
        <h1>Vyber si hru</h1>
        <a href="/kostky" class="btn-game"><h2>🎲 Kostky</h2></a>
        <a href="/prsi" class="btn-game"><h2>🃏 Prší</h2><p>(Brzy...)</p></a>
    </body>
    </html>
    """)

@app.route('/prsi')
def prsi():
    return "<h1>Prší</h1><p>Tady zatím nic není.</p><a href='/'>Zpět</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)