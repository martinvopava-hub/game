import eventlet
eventlet.monkey_patch()  # Důležité pro stabilitu na Renderu

import os
import random
from flask import Flask, render_template_string, request, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-tajemstvi-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY (pro zjednodušení v paměti) ---
# V reálné velké aplikaci by zde byla databáze
game_state = {
    'total': 0,
    'turn': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čekám na první hod...',
    'last_player': None
}

def vypocitej_vyber(vyber):
    if not vyber: return 0
    counts = {}
    for x in vyber: counts[x] = counts.get(x, 0) + 1
    
    body = 0
    if len(counts) == 6: return 2000  # Postupka

    for num, count in counts.items():
        if num == 1:
            if count < 3: body += count * 100
            else: body += 1000 * (2 ** (count - 3))
        elif num == 5:
            if count < 3: body += count * 50
            else: body += 500 * (2 ** (count - 3))
        else:
            if count >= 3:
                zaklad = num * 100
                body += zaklad * (2 ** (count - 3))
            else: return 0
    return body

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# --- SOCKET.IO UDÁLOSTI ---

@socketio.on('connect')
def handle_connect():
    # Při připojení pošleme hráči aktuální stav
    emit('update_game', game_state)

@socketio.on('roll_dice')
def handle_roll():
    global game_state
    game_state['current_roll'] = [random.randint(1, 6) for _ in range(game_state['dice_count'])]
    
    # Kontrola nuly (smrti)
    test_counts = {}
    for x in game_state['current_roll']: test_counts[x] = test_counts.get(x, 0) + 1
    mozne_body = any(n == 1 or n == 5 or cnt >= 3 for n, cnt in test_counts.items()) or len(test_counts) == 6

    if not mozne_body:
        game_state['msg'] = f"❌ NULA! Ztráta {game_state['turn']} bodů."
        game_state['turn'] = 0
        game_state['dice_count'] = 6
        game_state['current_roll'] = []
    else:
        game_state['msg'] = "Vyberte kostky a potvrďte."
    
    socketio.emit('update_game', game_state)

@socketio.on('keep_dice')
def handle_keep(data):
    global game_state
    indices = data.get('indices', [])
    selected_values = [game_state['current_roll'][i] for i in indices]
    
    points = vypocitej_vyber(selected_values)
    if points > 0:
        game_state['turn'] += points
        game_state['dice_count'] -= len(selected_values)
        if game_state['dice_count'] == 0: game_state['dice_count'] = 6
        game_state['current_roll'] = []
        game_state['msg'] = f"Získáno {points} bodů."
    else:
        game_state['msg'] = "⚠️ Neplatná kombinace!"
    
    socketio.emit('update_game', game_state)

@socketio.on('bank_points')
def handle_bank():
    global game_state
    if game_state['turn'] >= 350:
        game_state['total'] += game_state['turn']
        game_state['msg'] = f"💰 Zapsáno {game_state['turn']} bodů."
        game_state['turn'] = 0
        game_state['dice_count'] = 6
        game_state['current_roll'] = []
    else:
        game_state['msg'] = "⚠️ Minimum pro zápis je 350!"
    
    socketio.emit('update_game', game_state)

@socketio.on('reset_game')
def handle_reset():
    global game_state
    game_state = { 'total': 0, 'turn': 0, 'dice_count': 6, 'current_roll': [], 'msg': 'Hra restartována.', 'last_player': None }
    socketio.emit('update_game', game_state)

# --- HTML ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kostky MULTIPLAYER</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #121212; color: white; text-align: center; }
        .table { background: #1e3a1e; padding: 20px; border-radius: 20px; width: 400px; margin: 50px auto; border: 5px solid #3e2723; }
        .die { display: inline-block; width: 50px; height: 50px; line-height: 50px; background: white; color: black; 
               margin: 5px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 24px; }
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 5px 0 #b7950b; }
        .btn { width: 100%; padding: 10px; margin: 5px 0; font-weight: bold; cursor: pointer; border-radius: 5px; border: none; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
    </style>
</head>
<body>
    <div class="table">
        <h1 id="total">0</h1>
        <h3 id="turn" style="color: #2ecc71;">V tahu: 0</h3>
        <p id="msg" style="color: #f1c40f;">Načítání...</p>
        <div id="dice-container"></div>
        <hr>
        <div id="controls"></div>
        <button onclick="resetHru()" style="background:none; border:none; color:#666; cursor:pointer; margin-top:10px;">Resetovat vše</button>
    </div>

    <script>
        const socket = io();
        let selectedIndices = [];

        socket.on('update_game', (data) => {
            document.getElementById('total').innerText = data.total.toLocaleString();
            document.getElementById('turn').innerText = "V tahu: " + data.turn;
            document.getElementById('msg').innerText = data.msg;
            
            const container = document.getElementById('dice-container');
            container.innerHTML = '';
            data.current_roll.forEach((val, idx) => {
                const d = document.createElement('div');
                d.className = 'die' + (selectedIndices.includes(idx) ? ' selected' : '');
                d.innerText = val;
                d.onclick = () => {
                    if (selectedIndices.includes(idx)) selectedIndices = selectedIndices.filter(i => i !== idx);
                    else selectedIndices.push(idx);
                    renderButtons(data.current_roll.length > 0);
                    d.classList.toggle('selected');
                };
                container.appendChild(d);
            });
            renderButtons(data.current_roll.length > 0, data.turn);
        });

        function renderButtons(hasRoll, turn) {
            const ctrl = document.getElementById('controls');
            ctrl.innerHTML = '';
            if (!hasRoll) {
                ctrl.innerHTML = `<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT KOSTKAMI</button>`;
            } else {
                ctrl.innerHTML = `<button class="btn btn-keep" onclick="potvrditVyber()">POTVRDIT VÝBĚR</button>`;
            }
            if (turn > 0) {
                ctrl.innerHTML += `<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT DO BANKU</button>`;
            }
        }

        function potvrditVyber() {
            socket.emit('keep_dice', { indices: selectedIndices });
            selectedIndices = [];
        }

        function resetHru() { if(confirm("Opravdu resetovat hru pro všechny?")) socket.emit('reset_game'); }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)