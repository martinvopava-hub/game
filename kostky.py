import random
from flask import Blueprint, render_template_string, request
from flask_socketio import emit

# Definice Blueprintu
kostky_bp = Blueprint('kostky', __name__)

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

# Funkce, kterou zavoláme v app.py pro registraci socketů
def register_kostky_sockets(socketio):
    
    @socketio.on('join_game', namespace='/kostky')
    def handle_join(data):
        sid = request.sid
        name = data.get('name', 'Hráč').strip()[:12]
        if not any(p['id'] == sid for p in game['players']):
            game['players'].append({'id': sid, 'name': name})
            game['scores'][sid] = 0
            game['msg'] = f"Připojen {name}."
        emit('update', game, broadcast=True, namespace='/kostky')

    @socketio.on('roll_dice', namespace='/kostky')
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
            emit('update', game, broadcast=True, namespace='/kostky')
        else:
            emit('update', game, broadcast=True, namespace='/kostky')

    @socketio.on('select_die', namespace='/kostky')
    def handle_select(data):
        sid = request.sid
        if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
        idx = data.get('index')
        if idx in game['selected_indices']:
            game['selected_indices'].remove(idx)
        else:
            game['selected_indices'].append(idx)
        emit('update', game, broadcast=True, namespace='/kostky')

    @socketio.on('keep_dice', namespace='/kostky')
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
        emit('update', game, broadcast=True, namespace='/kostky')

    @socketio.on('bank_points', namespace='/kostky')
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
            emit('update', game, broadcast=True, namespace='/kostky')

    @socketio.on('reset_game', namespace='/kostky')
    def handle_reset():
        global game
        game.update({'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'selected_indices': [], 'msg': 'Restart.', 'winner': None, 'finisher_sid': None})
        emit('reload', broadcast=True, namespace='/kostky')

# --- HTML ŠABLONA ---
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
        .player-card { width: 300px; padding: 20px; border-radius: 15px; transition: 0.4s; background: #1a1a1a; border: 4px solid #444; text-align: center; }
        .player-card.active { border-color: #2ecc71; background: #1e3a1e; box-shadow: 0 0 25px #2ecc7166; transform: scale(1.05); }
        .die { width: 45px; height: 45px; line-height: 45px; background: white; color: black; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 22px; margin: 2px; display: inline-block;}
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 4px 0 #b7950b; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
    </style>
</head>
<body>
    <a href="/" style="color: #888; text-decoration: none;">← Zpět do menu</a>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" style="padding:10px; width:250px;" placeholder="Tvé jméno...">
        <button class="btn btn-roll" style="width:270px; margin-top:10px;" onclick="join()">VSTOUPIT</button>
    </div>
    <h2 id="global-msg" style="text-align:center; color:#f1c40f;"></h2>
    <div id="arena" class="arena"></div>
    <script>
        const socket = io('/kostky');
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
                card.className = `player-card ${isActive ? 'active' : ''}`;
                card.innerHTML = `<h3>${p.name} ${isMe ? '(Ty)' : ''}</h3><div style="font-size:30px">${g.scores[p.id]}</div><div id="dice-box-${idx}"></div>`;
                
                if(isMe && isActive && !g.winner) {
                   card.innerHTML += g.current_roll.length === 0 ? 
                   '<button class="btn btn-roll" onclick="socket.emit(\'roll_dice\')">HODIT</button>' :
                   '<button class="btn btn-keep" onclick="socket.emit(\'keep_dice\')">POTVRDIT</button>';
                   if(g.current_turn_pts >= 350) card.innerHTML += '<button class="btn btn-bank" onclick="socket.emit(\'bank_points\')">ZAPSAT</button>';
                }
                arena.appendChild(card);
                if(isActive && g.current_roll.length > 0) {
                    const box = document.getElementById(`dice-box-${idx}`);
                    g.current_roll.forEach((v, i) => {
                        const d = document.createElement('div');
                        d.className = 'die' + (g.selected_indices.includes(i) ? ' selected' : '');
                        d.innerText = v;
                        if(isMe) d.onclick = () => socket.emit('select_die', {index: i});
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