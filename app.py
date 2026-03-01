import eventlet
eventlet.monkey_patch()  # Musí být úplně první!

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-multiplayer-2026'
# Povolíme CORS pro bezproblémové připojení na Renderu
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY ---
game = {
    'players': [],       # Seznam {'id': sid, 'name': jméno}
    'scores': {},        # sid: celkové body
    'turn_index': 0,     # Kdo je na řadě
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čeká se na hráče...',
    'winner': None
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
    sid = request.sid
    name = data.get('name', 'Hráč').strip()[:15]
    if not any(p['id'] == sid for p in game['players']):
        game['players'].append({'id': sid, 'name': name})
        game['scores'][sid] = 0
        if len(game['players']) == 1:
            game['msg'] = f"Vítej {name}. Čekej na soupeře..."
        else:
            game['msg'] = f"Hra běží! Na řadě je {game['players'][game['turn_index']]['name']}"
    socketio.emit('update', game)

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid or game['winner']:
        return

    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    
    # Kontrola "smrti"
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    mozne = any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) or len(c) == 6
    
    if not mozne:
        name = game['players'][game['turn_index']]['name']
        game['msg'] = f"❌ NULA! {name} přichází o body."
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    else:
        game['msg'] = "Vyber bodované kostky."
    
    socketio.emit('update', game)

@socketio.on('keep_dice')
def handle_keep(data):
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    
    indices = data.get('indices', [])
    selected = [game['current_roll'][i] for i in indices]
    pts = vypocitej_body(selected)

    if pts > 0:
        game['current_turn_pts'] += pts
        game['dice_count'] -= len(selected)
        if game['dice_count'] == 0: game['dice_count'] = 6
        game['current_roll'] = []
        game['msg'] = f"Získáno {pts} bodů. Házej dál nebo zapiš."
    else:
        game['msg'] = "⚠️ Neplatná kombinace!"
    
    socketio.emit('update', game)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    
    if game['current_turn_pts'] >= 350:
        game['scores'][sid] += game['current_turn_pts']
        
        # Kontrola výhry 10 000
        if game['scores'][sid] >= 10000:
            game['winner'] = game['players'][game['turn_index']]['name']
            game['msg'] = f"🎉 {game['winner']} VYHRÁVÁ HRU!"
        else:
            game['current_turn_pts'] = 0
            game['dice_count'] = 6
            game['current_roll'] = []
            game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
            game['msg'] = f"Zapsáno. Na řadě je {game['players'][game['turn_index']]['name']}"
    else:
        game['msg'] = "⚠️ Musíš mít aspoň 350 bodů!"
    
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'msg': 'Hra restartována.', 'winner': None}
    socketio.emit('restart_client')

@socketio.on('disconnect')
def handle_disconnect():
    # Odstranění hráče při odpojení
    sid = request.sid
    game['players'] = [p for p in game['players'] if p['id'] != sid]
    if not game['players']: handle_reset()
    socketio.emit('update', game)

# --- HTML / JS ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Kostky Online 10000</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: white; text-align: center; margin: 0; }
        #login-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background: #1a1a1a; z-index: 100; display: flex; flex-direction: column; justify-content: center; align-items: center; }
        .table { background: #1e3a1e; padding: 25px; border-radius: 20px; width: 420px; margin: 40px auto; border: 6px solid #3e2723; box-shadow: 0 0 40px rgba(0,0,0,0.6); }
        .player-row { display: flex; justify-content: space-around; background: rgba(0,0,0,0.4); padding: 10px; border-radius: 10px; margin-bottom: 15px; font-size: 18px; }
        .active { color: #2ecc71; font-weight: bold; border-bottom: 2px solid #2ecc71; }
        .die { display: inline-block; width: 50px; height: 50px; line-height: 50px; background: white; color: black; margin: 6px; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 26px; transition: 0.2s; }
        .die.selected { background: #f1c40f; transform: translateY(-8px); box-shadow: 0 5px 0 #b7950b; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; font-weight: bold; cursor: pointer; border-radius: 8px; border: none; font-size: 16px; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { background: #444; color: #888; cursor: not-allowed; }
        input { padding: 12px; font-size: 18px; border-radius: 8px; border: none; margin-bottom: 10px; width: 250px; }
    </style>
</head>
<body>
    <div id="login-overlay">
        <h1>🎲 Kostky Online</h1>
        <input type="text" id="nick" placeholder="Tvoje přezdívka..." maxlength="15">
        <button class="btn btn-roll" style="width: 275px;" onclick="join()">VSTOUPIT DO HRY</button>
    </div>

    <div class="table">
        <div id="players" class="player-row"></div>
        <h2 id="msg" style="color: #f1c40f; min-height: 1.2em;"></h2>
        <div style="font-size: 14px; color: #aaa;">AKTUÁLNÍ TAH</div>
        <h1 id="turn-pts" style="margin: 5px 0; color: #2ecc71;">0</h1>
        
        <div id="dice-container" style="min-height: 70px; margin: 20px 0;"></div>
        
        <div id="controls"></div>
        <button onclick="resetGame()" style="background:none; border:none; color:#555; cursor:pointer; margin-top:20px;">Restartovat celou hru</button>
    </div>

    <script>
        const socket = io();
        let selectedIndices = [];

        function join() {
            const n = document.getElementById('nick').value;
            if(!n) return alert("Zadej jméno!");
            socket.emit('join_game', {name: n});
            document.getElementById('login-overlay').style.display = 'none';
        }

        socket.on('update', (g) => {
            const myTurn = g.players.length > 0 && g.players[g.turn_index].id === socket.id;
            
            // Hráči a skóre
            const pDiv = document.getElementById('players');
            pDiv.innerHTML = g.players.map((p, i) => 
                `<div class="${i === g.turn_index ? 'active' : ''}">${p.name}<br>${g.scores[p.id]}</div>`
            ).join('');

            document.getElementById('msg').innerText = g.msg;
            document.getElementById('turn-pts').innerText = g.current_turn_pts;

            // Kostky
            const dDiv = document.getElementById('dice-container');
            dDiv.innerHTML = '';
            g.current_roll.forEach((val, idx) => {
                const d = document.createElement('div');
                d.className = 'die' + (selectedIndices.includes(idx) ? ' selected' : '');
                d.innerText = val;
                if(myTurn && !g.winner) d.onclick = () => {
                    if(selectedIndices.includes(idx)) selectedIndices = selectedIndices.filter(i => i !== idx);
                    else selectedIndices.push(idx);
                    d.classList.toggle('selected');
                };
                dDiv.appendChild(d);
            });

            // Tlačítka
            const cDiv = document.getElementById('controls');
            cDiv.innerHTML = '';
            if(!g.winner && g.players.length >= 1) {
                if(g.current_roll.length === 0) {
                    cDiv.innerHTML = `<button class="btn btn-roll" ${!myTurn?'disabled':''} onclick="socket.emit('roll_dice')">HODIT KOSTKAMI (${g.dice_count})</button>`;
                } else {
                    cDiv.innerHTML = `<button class="btn btn-keep" ${!myTurn?'disabled':''} onclick="confirmKeep()">POTVRDIT VÝBĚR</button>`;
                }
                if(g.current_turn_pts > 0) {
                    cDiv.innerHTML += `<button class="btn btn-bank" ${!myTurn?'disabled':''} onclick="socket.emit('bank_points')">UKONČIT TAH A ZAPSAT</button>`;
                }
            } else if(g.winner) {
                cDiv.innerHTML = `<h2 style="color:#f1c40f">Vítěz: ${g.winner}!</h2>`;
            }
        });

        function confirmKeep() {
            if(selectedIndices.length === 0) return alert("Vyber aspoň jednu kostku!");
            socket.emit('keep_dice', {indices: selectedIndices});
            selectedIndices = [];
        }

        function resetGame() { if(confirm("Opravdu restartovat?")) socket.emit('reset_game'); }
        socket.on('restart_client', () => { window.location.reload(); });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)