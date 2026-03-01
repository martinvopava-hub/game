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
    'final_round': False,   # Aktivuje se při 10 000+
    'leader_sid': None,     # Kdo aktuálně drží nejvyšší skóre v dohrávce
    'players_done': []      # Seznam SID hráčů, co už dohráli svůj poslední pokus
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

def posun_tah():
    current_sid = game['players'][game['turn_index']]['id']
    game['players_done'].append(current_sid)
    
    # Najdeme dalšího hráče, který ještě není "done"
    starting_index = game['turn_index']
    while True:
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        next_sid = game['players'][game['turn_index']]['id']
        
        # Pokud jsme se vrátili ke stejnému hráči a nikdo jiný není volný, konec hry
        if game['turn_index'] == starting_index and next_sid in game['players_done']:
            # Vyhlášení absolutního vítěze
            leader_name = "Nikdo"
            for p in game['players']:
                if p['id'] == game['leader_sid']: leader_name = p['name']
            game['winner'] = leader_name
            game['msg'] = f"🏆 Konec hry! Vítězí {leader_name}!"
            break
            
        if next_sid not in game['players_done']:
            break

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
        game['msg'] = f"Připojen {name}. " + (f"Na řadě je {game['players'][0]['name']}" if len(game['players']) > 1 else "Čekej na soupeře.")
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
        game['dice_count'] = 6
        game['current_roll'] = []
        
        if game['final_round']:
            posun_tah()
        else:
            game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    else:
        game['msg'] = "Vyber kostky..."
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
        current_score = game['scores'][sid]
        
        # LOGIKA DOHRÁVKY
        if current_score >= 10000:
            if not game['final_round']:
                game['final_round'] = True
                game['leader_sid'] = sid
                game['players_done'] = [sid] # Ten kdo nahral 10k uz nehraje
                game['msg'] = f"🏁 DOHRÁVKA! {game['players'][game['turn_index']]['name']} nahrál {current_score}!"
            else:
                # Pokud někdo v dohrávce přehodí leadera
                leader_score = game['scores'][game['leader_sid']]
                if current_score > leader_score:
                    game['leader_sid'] = sid
                    # Resetujeme dohrávku pro ostatní (každý má znovu šanci přehodit nového leadera)
                    game['players_done'] = [sid]
                    game['msg'] = f"🔥 NOVÝ LÍDR! {game['players'][game['turn_index']]['name']} vede s {current_score}!"
        
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        
        if game['final_round']:
            posun_tah()
        else:
            game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    else:
        game['msg'] = "⚠️ Musíš mít aspoň 350!"
    
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {
        'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 
        'current_roll': [], 'msg': 'Restartováno.', 'winner': None, 
        'final_round': False, 'leader_sid': None, 'players_done': []
    }
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
    <title>Kostky Arena - Dohrávka</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: white; margin: 0; padding: 20px; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background: #111; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        
        .arena { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        
        .player-card { 
            width: 300px; padding: 20px; border-radius: 15px; transition: 0.4s; 
            background: #1a1a1a; border: 4px solid #444; position: relative;
            display: flex; flex-direction: column; align-items: center; text-align: center;
        }
        
        .player-card.active { 
            border-color: #2ecc71; background: #1e3a1e; 
            box-shadow: 0 0 25px rgba(46, 204, 113, 0.4); transform: scale(1.05); z-index: 10;
        }
        
        .player-card.inactive { border-color: #e74c3c; opacity: 0.6; }
        .player-card.done { border-color: #555; opacity: 0.4; filter: grayscale(1); }

        .score-badge { font-size: 40px; font-weight: bold; margin: 5px 0; }
        .turn-pts { font-size: 22px; color: #2ecc71; font-weight: bold; margin-bottom: 10px; min-height: 28px; }
        
        /* Grid pro kostky 3 a 3 */
        .dice-grid { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 10px; 
            justify-items: center; 
            margin: 15px 0;
            width: 100%;
        }
        
        .die { 
            width: 50px; height: 50px; line-height: 50px; background: white; color: black; 
            border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 24px;
            transition: 0.2s;
        }
        .die.selected { background: #f1c40f; transform: translateY(-5px); box-shadow: 0 4px 0 #b7950b; }
        
        .controls { width: 100%; }
        .btn { width: 100%; padding: 12px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .btn:disabled { display: none; }
        
        input { padding: 12px; font-size: 18px; border-radius: 8px; border: none; margin-bottom: 10px; width: 250px; }
        .leader-label { color: #f1c40f; font-weight: bold; font-size: 12px; margin-top: -5px; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🎲 Kostky Arena</h1>
        <input type="text" id="nick" placeholder="Tvé jméno..." maxlength="12">
        <button class="btn btn-roll" style="width:275px" onclick="join()">VSTOUPIT DO ARENY</button>
    </div>

    <h2 id="global-msg" style="text-align:center; color:#f1c40f; min-height: 1.5em;"></h2>
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
                const isActive = index === g.turn_index && !g.winner;
                const isLeader = p.id === game.leader_sid;
                const isDone = g.players_done.includes(p.id);
                const isMe = p.id === socket.id;
                
                const card = document.createElement('div');
                card.className = `player-card ${isActive ? 'active' : (isDone ? 'done' : 'inactive')}`;
                
                let content = `
                    <h3>${p.name} ${isMe ? '(Ty)' : ''}</h3>
                    ${isLeader ? '<div class="leader-label">⭐ AKTUÁLNÍ LÍDR ⭐</div>' : ''}
                    <div class="score-badge">${g.scores[p.id]}</div>
                    <div class="turn-pts">${isActive ? 'V tahu: ' + g.current_turn_pts : ''}</div>
                    <hr style="width:100%; border:0; border-top:1px solid rgba(255,255,255,0.1); margin:10px 0;">
                `;

                if (isActive) {
                    content += `<div class="dice-grid" id="dice-box"></div>`;
                    if (isMe) {
                        content += `
                            <div class="controls">
                                ${g.current_roll.length === 0 ? 
                                    `<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT KOSTKAMI (${g.dice_count})</button>` :
                                    `<button class="btn btn-keep" onclick="confirmKeep()">POTVRDIT VÝBĚR</button>`
                                }
                                ${g.current_turn_pts >= 350 ? `<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT BODY</button>` : ''}
                            </div>
                        `;
                    }
                }

                card.innerHTML = content;
                arena.appendChild(card);

                if (isActive && g.current_roll.length > 0) {
                    const dBox = card.querySelector('#dice-box');
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
            if(selectedIndices.length === 0) return alert("Vyber aspoň jednu!");
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