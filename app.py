import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-arena-final-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV HRY ---
game = {
    'players': [],       
    'scores': {},        
    'turn_index': 0,     
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čeká se na hráče...',
    'winner': None,
    'final_round': False,
    'target_score': 0,
    'players_finished': [] # Kdo už v dohazovacím kole hrál
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
    socketio.emit('update', game)

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid or game['winner']: return

    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    mozne = any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) or len(c) == 6
    
    if not mozne:
        name = game['players'][game['turn_index']]['name']
        game['msg'] = f"❌ NULA pro {name}!"
        game['current_turn_pts'] = 0
        ukonci_tah()
    else:
        game['msg'] = "Házej dál nebo zapiš."
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
    else:
        game['msg'] = "⚠️ Neplatná kombinace!"
    socketio.emit('update', game)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    
    if game['current_turn_pts'] >= 350:
        game['scores'][sid] += game['current_turn_pts']
        current_total = game['scores'][sid]
        
        # LOGIKA VÍTĚZSTVÍ / FINÁLNÍHO KOLA
        if not game['final_round'] and current_total >= 10000:
            game['final_round'] = True
            game['target_score'] = current_total
            game['players_finished'].append(sid)
            game['msg'] = f"🔥 {game['players'][game['turn_index']]['name']} dal {current_total}! Ostatní mají poslední šanci ho přehodit!"
        elif game['final_round']:
            if current_total > game['target_score']:
                game['winner'] = game['players'][game['turn_index']]['name']
                game['msg'] = f"🏆 NOVÝ VÍTĚZ! {game['winner']} přehodil cíl!"
            else:
                game['players_finished'].append(sid)
        
        if not game['winner']:
            game['current_turn_pts'] = 0
            ukonci_tah()
    else:
        game['msg'] = "Zápis až od 350 bodů!"
    socketio.emit('update', game)

def ukonci_tah():
    game['current_roll'] = []
    game['dice_count'] = 6
    game['current_turn_pts'] = 0
    
    # Najít dalšího hráče, který ještě nedohazoval
    original_index = game['turn_index']
    while True:
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        next_sid = game['players'][game['turn_index']]['id']
        
        # Pokud jsme prošli všechny a nikdo nepředběhl target_score
        if game['final_round'] and next_sid in game['players_finished']:
            if game['turn_index'] == original_index or len(game['players_finished']) >= len(game['players']):
                # Najdeme kdo má nejvíc
                best_sid = max(game['scores'], key=game['scores'].get)
                game['winner'] = next(p['name'] for p in game['players'] if p['id'] == best_sid)
                game['msg'] = f"🏁 Konec hry! Vítězí {game['winner']}."
                break
            continue
        break

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'msg': 'Restartováno.', 'winner': None, 'final_round': False, 'target_score': 0, 'players_finished': []}
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
    <title>Kostky Arena - Finále</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0b0b; color: white; margin: 0; padding: 20px; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background: #111; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        .arena { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        .player-card { width: 300px; padding: 20px; border-radius: 15px; transition: 0.4s; background: #1a1a1a; border: 4px solid #444; text-align: center; }
        .player-card.active { border-color: #2ecc71; background: #1e3a1e; box-shadow: 0 0 25px rgba(46, 204, 113, 0.4); transform: scale(1.05); }
        .player-card.inactive { border-color: #e74c3c; opacity: 0.6; }
        .target-mark { color: #f1c40f; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
        .score-badge { font-size: 40px; font-weight: bold; margin: 5px 0; }
        .turn-pts { font-size: 20px; color: #2ecc71; min-height: 24px; font-weight: bold; }
        #dice-box { display: flex; justify-content: center; gap: 8px; margin: 15px 0; min-height: 50px; }
        .die { width: 45px; height: 45px; line-height: 45px; background: white; color: black; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 22px; }
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 4px 0 #b7950b; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { display: none; }
        input { padding: 12px; font-size: 18px; border-radius: 8px; border: none; margin-bottom: 10px; width: 250px; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" placeholder="Tvé jméno..." maxlength="12">
        <button class="btn btn-roll" style="width:275px" onclick="join()">VSTOUPIT DO HRY</button>
    </div>

    <h2 id="global-msg" style="text-align:center; color:#f1c40f; min-height: 60px; padding: 0 20px;"></h2>
    <div id="arena" class="arena"></div>
    
    <div style="text-align:center; margin-top:40px;">
        <button onclick="if(confirm('Reset?')) socket.emit('reset_game')" style="color:#444; background:none; border:none; cursor:pointer;">Restartovat server</button>
    </div>

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

            g.players.forEach((p, index) => {
                const isActive = index === g.turn_index;
                const isMe = p.id === socket.id;
                const card = document.createElement('div');
                card.className = `player-card ${isActive ? 'active' : 'inactive'}`;
                
                let isTarget = g.final_round && g.scores[p.id] === g.target_score;

                card.innerHTML = `
                    <div class="target-mark">${isTarget ? '⭐ CÍL K PŘEKONÁNÍ ⭐' : ''}</div>
                    <h3>${p.name} ${isMe ? '(Ty)' : ''}</h3>
                    <div class="score-badge">${g.scores[p.id]}</div>
                    <div class="turn-pts">${isActive ? 'V tahu: ' + g.current_turn_pts : ''}</div>
                    <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
                    <div id="dice-box-${index}"></div>
                `;

                if (isActive && isMe && !g.winner) {
                    const ctrl = document.createElement('div');
                    ctrl.className = 'controls';
                    ctrl.innerHTML = `
                        ${g.current_roll.length === 0 ? 
                            `<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT KOSTKAMI</button>` :
                            `<button class="btn btn-keep" onclick="confirmKeep()">POTVRDIT VÝBĚR</button>`
                        }
                        ${g.current_turn_pts >= 350 ? `<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT BODY</button>` : ''}
                    `;
                    card.appendChild(ctrl);
                }
                arena.appendChild(card);

                if (isActive && g.current_roll.length > 0) {
                    const dBox = document.getElementById(`dice-box-${index}`);
                    g.current_roll.forEach((val, i) => {
                        const d = document.createElement('div');
                        d.className = 'die' + (selectedIndices.includes(i) ? ' selected' : '');
                        d.innerText = val;
                        if (isMe) d.onclick = () => {
                            if(selectedIndices.includes(i)) selectedIndices = selectedIndices.filter(x => x !== i);
                            else selectedIndices.push(i);
                            d.classList.toggle('selected');
                        };
                        dBox.appendChild(d);
                    });
                }
            });
        });

        function confirmKeep() {
            socket.emit('keep_dice', {indices: selectedIndices});
            selectedIndices = [];
        }
        socket.on('reload', () => location.reload());
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)