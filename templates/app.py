





import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-live-sync-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY ---
game = {
    'players': [],       
    'scores': {},        
    'turn_index': 0,     
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'selected_indices': [], # Kostky, na které hráč PRÁVĚ kliká
    'msg': 'Čeká se na hráče...',
    'winner': None,
    'finisher_sid': None 
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
    name = data.get('name', 'Hráč').strip()[:12]
    if not any(p['id'] == sid for p in game['players']):
        game['players'].append({'id': sid, 'name': name})
        game['scores'][sid] = 0
        game['msg'] = f"Připojen {name}."
    socketio.emit('update', game)

def next_turn():
    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    game['selected_indices'] = [] # Reset výběru pro dalšího
    if game['finisher_sid'] and game['players'][game['turn_index']]['id'] == game['finisher_sid']:
        best_sid = max(game['scores'], key=game['scores'].get)
        winner_name = next(p['name'] for p in game['players'] if p['id'] == best_sid)
        game['winner'] = winner_name
        game['msg'] = f"🏆 VÍTĚZ: {winner_name}!"
    else:
        game['msg'] = f"Na řadě je {game['players'][game['turn_index']]['name']}."

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid or game['winner']: return
    game['selected_indices'] = []
    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    mozne = any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) or len(c) == 6
    if not mozne:
        game['msg'] = "❌ NULA!"
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        next_turn()
    socketio.emit('update', game)

@socketio.on('select_die')
def handle_select(data):
    sid = request.sid
    # Pouze hráč na řadě může měnit výběr
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    idx = data.get('index')
    if idx in game['selected_indices']:
        game['selected_indices'].remove(idx)
    else:
        game['selected_indices'].append(idx)
    socketio.emit('update', game)

@socketio.on('keep_dice')
def handle_keep():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    selected_vals = [game['current_roll'][i] for i in game['selected_indices']]
    pts = vypocitej_body(selected_vals)
    if pts > 0:
        game['current_turn_pts'] += pts
        game['dice_count'] -= len(game['selected_indices'])
        if game['dice_count'] == 0: game['dice_count'] = 6
        game['current_roll'] = []
        game['selected_indices'] = []
    else:
        game['msg'] = "⚠️ Neplatná kombinace!"
    socketio.emit('update', game)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    if game['current_turn_pts'] >= 350:
        game['scores'][sid] += game['current_turn_pts']
        if game['scores'][sid] >= 10000 and game['finisher_sid'] is None:
            game['finisher_sid'] = sid
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        next_turn()
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'selected_indices': [], 'msg': 'Restart.', 'winner': None, 'finisher_sid': None}
    socketio.emit('reload')

@socketio.on('disconnect')
def handle_disc():
    game['players'] = [p for p in game['players'] if p['id'] != request.sid]
    if not game['players']: handle_reset()
    socketio.emit('update', game)

# --- HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kostky Arena LIVE</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: white; margin: 0; padding: 20px; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background: #111; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        .arena { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        .player-card { width: 300px; padding: 20px; border-radius: 15px; transition: 0.4s; background: #1a1a1a; border: 4px solid #444; text-align: center; }
        .player-card.active { border-color: #2ecc71; background: #1e3a1e; box-shadow: 0 0 25px #2ecc7166; transform: scale(1.05); }
        .player-card.inactive { border-color: #e74c3c; opacity: 0.6; filter: grayscale(0.5); }
        .player-card.finisher { border-color: #f1c40f !important; box-shadow: 0 0 15px #f1c40f; opacity: 1; filter: none; }
        .score-badge { font-size: 40px; font-weight: bold; margin: 10px 0; }
        .turn-pts { font-size: 20px; color: #2ecc71; min-height: 24px; }
        #dice-box { display: flex; justify-content: center; gap: 5px; margin: 15px 0; min-height: 55px; }
        .die { width: 45px; height: 45px; line-height: 45px; background: white; color: black; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 22px; transition: 0.1s; }
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 4px 0 #b7950b; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { display: none; }
        input { padding: 12px; font-size: 18px; border-radius: 8px; margin-bottom: 10px; width: 250px; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" placeholder="Tvé jméno..." maxlength="12">
        <button class="btn btn-roll" style="width:275px" onclick="join()">VSTOUPIT</button>
    </div>
    <h2 id="global-msg" style="text-align:center; color:#f1c40f; min-height: 35px;"></h2>
    <div id="arena" class="arena"></div>
    <div style="text-align:center; margin-top:40px;"><button onclick="socket.emit('reset_game')" style="color:#444; background:none; border:none; cursor:pointer;">Restartovat</button></div>

    <script>
        const socket = io();
        function join() {
            const n = document.getElementById('nick').value;
            if(n) { socket.emit('join_game', {name: n}); document.getElementById('login').style.display = 'none'; }
        }

        socket.on('update', (g) => {
            document.getElementById('global-msg').innerText = g.msg;
            const arena = document.getElementById('arena');
            arena.innerHTML = '';

            g.players.forEach((p, idx) => {
                const isActive = idx === g.turn_index;
                const isMe = p.id === socket.id;
                const card = document.createElement('div');
                card.className = `player-card ${isActive ? 'active' : 'inactive'} ${p.id === g.finisher_sid ? 'finisher' : ''}`;
                
                let content = `
                    <h3>${p.name} ${isMe ? '(Ty)' : ''}</h3>
                    <div class="score-badge">${g.scores[p.id]}</div>
                    <div class="turn-pts">${isActive ? 'V tahu: ' + g.current_turn_pts : ''}</div>
                    <hr style="border:0; border-top:1px solid #333; margin:15px 0;">
                `;

                if (isActive) {
                    content += `<div id="dice-box"></div>`;
                    if (isMe && !g.winner) {
                        content += `
                            <div class="controls">
                                ${g.current_roll.length === 0 ? 
                                    `<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT KOSTKAMI</button>` :
                                    `<button class="btn btn-keep" onclick="socket.emit('keep_dice')">POTVRDIT VÝBĚR</button>`
                                }
                                ${g.current_turn_pts >= 350 ? `<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT BODY</button>` : ''}
                            </div>
                        `;
                    }
                }
                if(g.winner === p.name) content += `<h2 style="color:#f1c40f">VÍTĚZ!</h2>`;
                card.innerHTML = content;
                arena.appendChild(card);

                if (isActive && g.current_roll.length > 0) {
                    const dBox = card.querySelector('#dice-box');
                    g.current_roll.forEach((val, i) => {
                        const d = document.createElement('div');
                        // Tady se kostka označí, i když kliká někdo jiný!
                        const isSelected = g.selected_indices.includes(i);
                        d.className = 'die' + (isSelected ? ' selected' : '');
                        d.innerText = val;
                        if (isMe && !g.winner) d.onclick = () => socket.emit('select_die', {index: i});
                        dBox.appendChild(d);
                    });
                }
            });
        });
        socket.on('reload', () => location.reload());
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)