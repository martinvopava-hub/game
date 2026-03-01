import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-pro-hrace-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- HERNÍ STAV ---
game = {
    'players': [],      # Seznam slovníků {'id': sid, 'name': jméno}
    'turn_index': 0,    # Index hráče, který je na řadě
    'total_scores': {}, # sid: skóre
    'current_turn_points': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čekáme na hráče...',
    'game_started': False
}

def vypocitej_body(vyber):
    if not vyber: return 0
    counts = {x: vyber.count(x) for x in set(vyber)}
    body = 0
    if len(counts) == 6: return 2000
    for num, count in counts.items():
        if num == 1:
            body += (1000 * (2**(count-3)) if count >= 3 else count * 100)
        elif num == 5:
            body += (500 * (2**(count-3)) if count >= 3 else count * 50)
        elif count >= 3:
            body += (num * 100) * (2**(count-3))
        else: return 0
    return body

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join_game')
def handle_join(data):
    name = data.get('name', 'Anonym').strip()[:15]
    sid = request.sid
    if not any(p['id'] == sid for p in game['players']):
        game['players'].append({'id': sid, 'name': name})
        game['total_scores'][sid] = 0
        if len(game['players']) >= 2:
            game['game_started'] = True
            game['msg'] = f"Hra začíná! Na řadě je {game['players'][0]['name']}"
    socketio.emit('update', game)

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    if game['players'][game['turn_index']]['id'] != sid: return

    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    
    # Kontrola "smrti"
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    if not any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) and len(c) < 6:
        game['msg'] = f"❌ NULA! {game['players'][game['turn_index']]['name']} ztratil body."
        game['current_turn_points'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    else:
        game['msg'] = f"{game['players'][game['turn_index']]['name']} hází..."
    
    socketio.emit('update', game)

@socketio.on('keep_dice')
def handle_keep(data):
    sid = request.sid
    if game['players'][game['turn_index']]['id'] != sid: return
    
    indices = data.get('indices', [])
    vals = [game['current_roll'][i] for i in indices]
    points = vypocitej_body(vals)

    if points > 0:
        game['current_turn_points'] += points
        game['dice_count'] -= len(vals)
        if game['dice_count'] == 0: game['dice_count'] = 6
        game['current_roll'] = []
        game['msg'] = f"Pěkně! {points} bodů."
    else:
        game['msg'] = "⚠️ Neplatná kombinace!"
    
    socketio.emit('update', game)

@socketio.on('bank')
def handle_bank():
    sid = request.sid
    if game['players'][game['turn_index']]['id'] != sid: return
    
    if game['current_turn_points'] >= 350:
        game['total_scores'][sid] += game['current_turn_points']
        game['current_turn_points'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        game['msg'] = f"Zapsáno! Teď hraje {game['players'][game['turn_index']]['name']}"
    else:
        game['msg'] = "Potřebuješ aspoň 350!"
    
    socketio.emit('update', game)

@socketio.on('disconnect')
def handle_disc():
    global game
    game['players'] = [p for p in game['players'] if p['id'] != request.sid]
    if not game['players']:
        game['game_started'] = False
        game['turn_index'] = 0

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)




    HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kostky Online</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: white; text-align: center; }
        .game-box { background: #2d5a27; padding: 25px; border-radius: 15px; width: 450px; margin: 30px auto; border: 6px solid #4e342e; }
        .die { display: inline-block; width: 50px; height: 50px; line-height: 50px; background: white; color: black; 
               margin: 6px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 22px; transition: 0.2s; }
        .die.selected { background: #f1c40f; transform: translateY(-8px); box-shadow: 0 5px 0 #b7950b; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; font-weight: bold; cursor: pointer; border-radius: 8px; border: none; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { background: #555; cursor: not-allowed; }
        .player-list { display: flex; justify-content: space-around; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 10px; margin-bottom: 15px; }
        .active-p { border-bottom: 3px solid #f1c40f; color: #f1c40f; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background:#1a1a1a; z-index:100; display:flex; flex-direction:column; justify-content:center; align-items:center; }
    </style>
</head>
<body>
    <div id="login">
        <h2>Zadej svou přezdívku</h2>
        <input type="text" id="nick" style="padding:10px; font-size:18px; border-radius:5px;"><br>
        <button class="btn btn-roll" style="width:200px;" onclick="join()">Vstoupit do hry</button>
    </div>

    <div class="game-box">
        <div id="player-list" class="player-list"></div>
        <h3 id="msg" style="color: #f1c40f; height: 24px;"></h3>
        <h2 id="turn-points" style="color: #2ecc71;">V tahu: 0</h2>
        <div id="dice-container" style="min-height: 70px;"></div>
        <div id="actions"></div>
    </div>

    <script>
        const socket = io();
        let myId = null;
        let selectedIndices = [];

        socket.on('connect', () => { myId = socket.id; });

        function join() {
            const name = document.getElementById('nick').value;
            if(!name) return alert("Zadej jméno!");
            socket.emit('join_game', { name: name });
            document.getElementById('login').style.display = 'none';
        }

        socket.on('update', (g) => {
            const isMyTurn = g.players.length > 0 && g.players[g.turn_index].id === socket.id;
            
            // Update hráčů
            const plist = document.getElementById('player-list');
            plist.innerHTML = g.players.map((p, i) => 
                `<div class="${i === g.turn_index ? 'active-p' : ''}">${p.name}: ${g.total_scores[p.id]}</div>`
            ).join('');

            document.getElementById('msg').innerText = g.msg;
            document.getElementById('turn-points').innerText = "V tahu: " + g.current_turn_points;

            // Vykreslení kostek
            const container = document.getElementById('dice-container');
            container.innerHTML = '';
            g.current_roll.forEach((val, idx) => {
                const d = document.createElement('div');
                d.className = 'die' + (selectedIndices.includes(idx) ? ' selected' : '');
                d.innerText = val;
                if(isMyTurn) d.onclick = () => {
                    d.classList.toggle('selected');
                    if (selectedIndices.includes(idx)) selectedIndices = selectedIndices.filter(i => i !== idx);
                    else selectedIndices.push(idx);
                };
                container.appendChild(d);
            });

            // Tlačítka (aktivní jen pro hráče na řadě)
            const acts = document.getElementById('actions');
            acts.innerHTML = '';
            if(g.game_started) {
                if(g.current_roll.length === 0) {
                    acts.innerHTML += `<button class="btn btn-roll" ${!isMyTurn?'disabled':''} onclick="socket.emit('roll_dice')">HODIT KOSTKAMI</button>`;
                } else {
                    acts.innerHTML += `<button class="btn btn-keep" ${!isMyTurn?'disabled':''} onclick="keep()">POTVRDIT VÝBĚR</button>`;
                }
                if(g.current_turn_points > 0) {
                    acts.innerHTML += `<button class="btn btn-bank" ${!isMyTurn?'disabled':''} onclick="socket.emit('bank')">UKONČIT TAH A ZAPSAT</button>`;
                }
            }
        });

        function keep() {
            socket.emit('keep_dice', { indices: selectedIndices });
            selectedIndices = [];
        }
    </script>
</body>
</html>
"""