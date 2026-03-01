import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-finale-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY ---
game = {
    'players': [],       # {'id': sid, 'name': jméno, 'finished': bool}
    'scores': {},        # sid: body
    'turn_index': 0,     
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čeká se na hráče...',
    'last_round': False, # Aktivuje se po 10 000 bodech
    'target_score': 10000,
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

def next_turn():
    start_index = game['turn_index']
    while True:
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        # Pokud jsme prošli všechny a nikdo už nemůže hrát (v dohrávce)
        if game['turn_index'] == start_index and game['players'][game['turn_index']].get('finished'):
            urci_vitezne_poradi()
            break
        # Pokud hráč ještě neukončil své dohazovací kolo
        if not game['players'][game['turn_index']].get('finished'):
            break

def urci_vitezne_poradi():
    best_sid = max(game['scores'], key=game['scores'].get)
    for p in game['players']:
        if p['id'] == best_sid:
            game['winner'] = p['name']
            game['msg'] = f"🏆 KONEC HRY! Vítězí {p['name']} s {game['scores'][best_sid]} body!"
            break

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    name = data.get('name', 'Hráč').strip()[:12]
    if not any(p['id'] == sid for p in game['players']):
        game['players'].append({'id': sid, 'name': name, 'finished': False})
        game['scores'][sid] = 0
        game['msg'] = f"Připojen {name}."
    socketio.emit('update', game)

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    curr_p = game['players'][game['turn_index']]
    if curr_p['id'] != sid or game['winner']: return

    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    mozne = any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) or len(c) == 6
    
    if not mozne:
        game['msg'] = f"❌ NULA pro {curr_p['name']}!"
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        if game['last_round']: curr_p['finished'] = True
        next_turn()
    else:
        game['msg'] = "Vyber kostky..."
    socketio.emit('update', game)

@socketio.on('keep_dice')
def handle_keep(data):
    sid = request.sid
    if game['players'][game['turn_index']]['id'] != sid: return
    indices = data.get('indices', [])
    selected = [game['current_roll'][i] for i in indices]
    pts = vypocitej_body(selected)

    if pts > 0:
        game['current_turn_pts'] += pts
        game['dice_count'] -= len(selected)
        if game['dice_count'] == 0: game['dice_count'] = 6
        game['current_roll'] = []
    socketio.emit('update', game)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    curr_p = game['players'][game['turn_index']]
    if curr_p['id'] != sid: return
    
    if game['current_turn_pts'] >= 350:
        game['scores'][sid] += game['current_turn_pts']
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        
        # Aktivace dohrávky
        if game['scores'][sid] >= game['target_score'] and not game['last_round']:
            game['last_round'] = True
            game['msg'] = f"🔥 DOHRÁVKA! {curr_p['name']} má {game['scores'][sid]}. Ostatní dohazují!"
            curr_p['finished'] = True # Ten, kdo nahral 10k, uz nehraje
        elif game['last_round']:
            curr_p['finished'] = True # V dohrávce má každý jen jeden zápis
            
        next_turn()
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'msg': 'Restartováno.', 'winner': None, 'last_round': False, 'target_score': 10000}
    socketio.emit('reload')

@socketio.on('disconnect')
def handle_disc():
    game['players'] = [p for p in game['players'] if p['id'] != request.sid]
    socketio.emit('update', game)

# --- HTML ŠABLONA ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Kostky Arena 10000</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: white; margin: 0; padding: 20px; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background: #111; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        .arena { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        
        .player-card { 
            width: 320px; padding: 20px; border-radius: 15px; transition: 0.4s; 
            background: #1a1a1a; border: 4px solid #444; text-align: center;
        }
        .player-card.active { border-color: #2ecc71; background: #1e3a1e; box-shadow: 0 0 25px rgba(46,204,113,0.3); transform: scale(1.03); }
        .player-card.inactive { border-color: #e74c3c; opacity: 0.6; }
        .player-card.finished { border-color: #f1c40f; opacity: 0.8; background: #2c2c00; }

        .score-badge { font-size: 45px; font-weight: bold; margin: 10px 0; color: #fff; }
        .turn-pts { font-size: 22px; color: #2ecc71; font-weight: bold; margin-bottom: 10px; }
        
        /* Grid pro kostky 3x2 */
        .dice-grid { 
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; 
            justify-items: center; align-items: center; margin: 20px auto; width: fit-content;
        }
        
        .die { 
            width: 55px; height: 55px; line-height: 55px; background: white; color: black; 
            border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 28px; 
            box-shadow: 0 4px 0 #ccc; transition: 0.1s;
        }
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 5px 0 #b7950b; }
        
        .btn { width: 100%; padding: 14px; margin: 6px 0; border-radius: 10px; border: none; font-weight: bold; cursor: pointer; font-size: 16px; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { display: none; }
        input { padding: 12px; font-size: 18px; border-radius: 8px; border: none; margin-bottom: 10px; width: 250px; background: #333; color: white; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" placeholder="Tvé jméno..." maxlength="12">
        <button class="btn btn-roll" style="width:275px" onclick="join()">VSTOUPIT</button>
    </div>

    <h2 id="global-msg" style="text-align:center; color:#f1c40f; min-height: 40px;"></h2>
    <div id="arena" class="arena"></div>

    <script>
        const socket = io();
        let selectedIndices = [];

        function join() {
            const n = document.getElementById('nick').value;
            if(!n) return;
            socket.emit('join_game', {name: n});
            document.getElementById('login').style.display = 'none';
        }

        socket.on('update', (g) => {
            document.getElementById('global-msg').innerText = g.msg;
            const arena = document.getElementById('arena');
            arena.innerHTML = '';

            g.players.forEach((p, idx) => {
                const isActive = idx === g.turn_index;
                const isMe = p.id === socket.id;
                const card = document.createElement('div');
                card.className = `player-card ${isActive ? 'active' : (p.finished ? 'finished' : 'inactive')}`;
                
                card.innerHTML = `
                    <h2 style="margin:0">${p.name} ${isMe ? ' (Já)' : ''}</h2>
                    <div class="score-badge">${g.scores[p.id]}</div>
                    <div class="turn-pts">${isActive ? 'V tahu: ' + g.current_turn_pts : (p.finished ? 'DOHRÁNO' : '')}</div>
                `;

                if (isActive && !g.winner) {
                    const dGrid = document.createElement('div');
                    dGrid.className = 'dice-grid';
                    g.current_roll.forEach((val, i) => {
                        const d = document.createElement('div');
                        d.className = 'die' + (selectedIndices.includes(i) ? ' selected' : '');
                        d.innerText = val;
                        if (isMe) d.onclick = () => {
                            if(selectedIndices.includes(i)) selectedIndices = selectedIndices.filter(x => x !== i);
                            else selectedIndices.push(i);
                            socket.emit('keep_dice', {indices: selectedIndices});
                        };
                        dGrid.appendChild(d);
                    });
                    card.appendChild(dGrid);

                    if (isMe) {
                        const ctrl = document.createElement('div');
                        if (g.current_roll.length === 0) {
                            ctrl.innerHTML = `<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT (${g.dice_count})</button>`;
                        } else {
                            ctrl.innerHTML = `<button class="btn btn-keep" onclick="selectedIndices=[]; socket.emit('update_game_state');">POTVRDIT VÝBĚR</button>`;
                        }
                        if (g.current_turn_pts >= 350) {
                            ctrl.innerHTML += `<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT A KONČIT</button>`;
                        }
                        card.appendChild(ctrl);
                    }
                }
                arena.appendChild(card);
            });
        });

        socket.on('reload', () => location.reload());
    </script>
</body>
</html>