import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-2026-fix'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY KOSTKY ---
game = {
    'players': [],
    'scores': {},
    'turn_index': 0,
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'selected_indices': [],
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

# --- ROUTY (STRÁNKY) ---

@app.route('/')
def menu():
    return render_template_string(HTML_MENU)

@app.route('/kostky_hram')
def kostky_page():
    return render_template_string(HTML_KOSTKY)

@app.route('/prsi')
def prsi_page():
    return "<h1>🃏 Prší</h1><p>Tato hra se připravuje.</p><a href='/'>Zpět do menu</a>"

# --- SOCKET.IO UDÁLOSTI ---

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    name = data.get('name', 'Hráč').strip()[:12]
    if not any(p['id'] == sid for p in game['players']):
        game['players'].append({'id': sid, 'name': name})
        game['scores'][sid] = 0
        game['msg'] = f"Připojen {name}."
    socketio.emit('update', game)

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
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        socketio.emit('update', game)
    else:
        socketio.emit('update', game)

@socketio.on('select_die')
def handle_select(data):
    sid = request.sid
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
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game.update({'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'selected_indices': [], 'msg': 'Restart.', 'winner': None, 'finisher_sid': None})
    socketio.emit('reload')

# --- ŠABLONY ---

HTML_MENU = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Herní Portál</title>
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
    <a href="/kostky_hram" class="btn-game"><h2>🎲 Kostky</h2></a>
    <a href="/prsi" class="btn-game"><h2>🃏 Prší</h2></a>
</body>
</html>
"""

HTML_KOSTKY = """
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
        .player-card { width: 300px; padding: 20px; border-radius: 15px; background: #1a1a1a; border: 4px solid #444; text-align: center; }
        .player-card.active { border-color: #2ecc71; background: #1e3a1e; }
        .die { width: 45px; height: 45px; line-height: 45px; background: white; color: black; border-radius: 8px; font-weight: bold; cursor: pointer; display: inline-block; margin: 5px; font-size: 22px; }
        .die.selected { background: #f1c40f; box-shadow: 0 4px 0 #b7950b; transform: translateY(-3px); }
        .btn { width: 100%; padding: 12px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; }
        .btn-roll { background: #2ecc71; color: white; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" placeholder="Tvé jméno..." style="padding:12px; width:250px; font-size:16px;">
        <button class="btn btn-roll" style="width:278px; margin-top:10px;" onclick="joinGame()">VSTOUPIT</button>
    </div>
    
    <div style="text-align:left;"><a href="/" style="color: #888; text-decoration: none;">← Zpět do menu</a></div>
    <h2 id="global-msg" style="text-align:center; color:#f1c40f; min-height:35px;"></h2>
    <div id="arena" class="arena"></div>

    <script>
        const socket = io();

        function joinGame() {
            const n = document.getElementById('nick').value;
            if(n) {
                socket.emit('join_game', {name: n});
                document.getElementById('login').style.display = 'none';
            }
        }

        socket.on('update', (g) => {
            document.getElementById('global-msg').innerText = g.msg;
            const arena = document.getElementById('arena');
            arena.innerHTML = '';

            g.players.forEach((p, idx) => {
                const isActive = idx === g.turn_index;
                const isMe = p.id === socket.id;
                const card = document.createElement('div');
                card.className = `player-card ${isActive ? 'active' : ''}`;
                
                let content = `
                    <h3>${p.name} ${isMe ? '(Ty)' : ''}</h3>
                    <div style="font-size:40px; font-weight:bold; margin:10px 0;">${g.scores[p.id]}</div>
                    <div style="color:#2ecc71; height:25px;">${isActive ? 'V tahu: ' + g.current_turn_pts : ''}</div>
                    <div id="dice-box-${idx}" style="min-height:60px; margin:15px 0;"></div>
                `;

                if (isActive && isMe && !g.winner) {
                    content += `
                        <div class="controls">
                            ${g.current_roll.length === 0 ? 
                                '<button class="btn btn-roll" onclick="socket.emit(\'roll_dice\')">HODIT KOSTKAMI</button>' :
                                '<button class="btn" style="background:#3498db; color:white;" onclick="socket.emit(\'keep_dice\')">POTVRDIT VÝBĚR</button>'
                            }
                            ${g.current_turn_pts >= 350 ? '<button class="btn" style="background:#e67e22; color:white;" onclick="socket.emit(\'bank_points\')">ZAPSAT BODY</button>' : ''}
                        </div>
                    `;
                }
                
                if(g.winner === p.name) content += `<h2 style="color:#f1c40f">VÍTĚZ!</h2>`;
                card.innerHTML = content;
                arena.appendChild(card);

                if (isActive && g.current_roll.length > 0) {
                    const box = document.getElementById(`dice-box-${idx}`);
                    g.current_roll.forEach((val, i) => {
                        const d = document.createElement('div');
                        const isSelected = g.selected_indices.includes(i);
                        d.className = 'die' + (isSelected ? ' selected' : '');
                        d.innerText = val;
                        if (isMe && !g.winner) d.onclick = () => socket.emit('select_die', {index: i});
                        box.appendChild(d);
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
    socketio.run(app, host='0.0.0.0', port=port, debug=True)