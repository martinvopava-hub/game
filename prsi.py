import random
from flask import Blueprint, render_template_string, request

prsi_bp = Blueprint('prsi', __name__)

# --- LOGIKA KARET ---
SUITS = ['Srdce', 'Kule', 'Žaludy', 'Zelené']
VALUES = ['7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def vytvor_balicek():
    balicek = [{'suit': s, 'val': v} for s in SUITS for v in VALUES]
    random.shuffle(balicek)
    return balicek

# --- STAV HRY ---
game = {
    'players': [],
    'deck': [],
    'discard': [],
    'turn_index': 0,
    'msg': 'Čeká se na hráče...',
    'winner': None,
    'penalty': 0, # Pro sedmy (2, 4, 6... karet)
    'skip_next': False # Pro esa
}

@prsi_bp.route('/prsi_hram')
def index():
    return render_template_string(HTML_PRSI)

def register_prsi_sockets(socketio):
    
    @socketio.on('join_prsi')
    def handle_join(data):
        sid = request.sid
        name = data.get('name', 'Hráč').strip()[:12]
        if not any(p['id'] == sid for p in game['players']) and len(game['players']) < 4:
            # Rozdáme 4 karty novému hráči
            if not game['deck']: 
                game['deck'] = vytvor_balicek()
                game['discard'] = [game['deck'].pop()]
            
            hand = [game['deck'].pop() for _ in range(4)]
            game['players'].append({'id': sid, 'name': name, 'hand': hand})
            game['msg'] = f"{name} se připojil."
        socketio.emit('update_prsi', game)

    @socketio.on('play_card')
    def handle_play(data):
        sid = request.sid
        if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
        
        card_idx = data.get('idx')
        player = game['players'][game['turn_index']]
        card = player['hand'][card_idx]
        top_card = game['discard'][-1]

        # Základní pravidlo: stejná barva nebo stejná hodnota
        if card['suit'] == top_card['suit'] or card['val'] == top_card['val'] or card['val'] == 'Q':
            player['hand'].pop(card_idx)
            game['discard'].append(card)
            
            # Kontrola výhry
            if not player['hand']:
                game['winner'] = player['name']
                game['msg'] = f"🏆 {player['name']} VYHRÁL!"
            else:
                # Speciální karty (zjednodušeně)
                if card['val'] == '7': game['penalty'] += 2
                if card['val'] == 'A': game['skip_next'] = True
                
                game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
                game['msg'] = f"Na řadě je {game['players'][game['turn_index']]['name']}."
            
            socketio.emit('update_prsi', game)

    @socketio.on('draw_card')
    def handle_draw():
        sid = request.sid
        if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
        
        player = game['players'][game['turn_index']]
        # Lízání (buď trest za sedmu nebo 1 karta)
        num_to_draw = max(1, game['penalty'])
        for _ in range(num_to_draw):
            if not game['deck']: # Pokud dojde balíček, otočíme odhazovací
                last = game['discard'].pop()
                game['deck'] = game['discard']
                random.shuffle(game['deck'])
                game['discard'] = [last]
            
            player['hand'].append(game['deck'].pop())
        
        game['penalty'] = 0
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
        socketio.emit('update_prsi', game)

# --- HTML ŠABLONA ---
HTML_PRSI = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Prší Online</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: sans-serif; background: #0e3d1a; color: white; text-align: center; }
        .hand { display: flex; justify-content: center; gap: 10px; margin-top: 50px; flex-wrap: wrap; }
        .card { 
            width: 80px; height: 120px; background: white; color: black; 
            border-radius: 10px; border: 2px solid #333; cursor: pointer;
            display: flex; flex-direction: column; justify-content: center;
            font-weight: bold; font-size: 20px;
        }
        .card.Srdce, .card.Kule { color: red; }
        .top-card-box { margin: 30px auto; width: 100px; height: 140px; border: 4px solid #f1c40f; border-radius: 15px; background: rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; }
        #login { position: fixed; top:0; left:0; width:100%; height:100%; background: #111; z-index:1000; display:flex; flex-direction:column; align-items:center; justify-content:center; }
    </style>
</head>
<body>
    <div id="login">
        <h1>🃏 Prší Arena</h1>
        <input type="text" id="nick" placeholder="Jméno...">
        <button onclick="join()">HRÁT</button>
    </div>

    <a href="/" style="color: white; text-decoration: none;">← Menu</a>
    <h2 id="msg"></h2>
    
    <div style="display: flex; justify-content: center; align-items: center; gap: 50px;">
        <div><h3>Balíček</h3><div class="card" onclick="socket.emit('draw_card')" style="background: #222; color: white;">🂠</div></div>
        <div><h3>V balíku</h3><div id="top-card" class="top-card-box"></div></div>
    </div>

    <div id="my-hand" class="hand"></div>

    <script>
        const socket = io();
        function join() {
            const n = document.getElementById('nick').value;
            if(n) { socket.emit('join_prsi', {name: n}); document.getElementById('login').style.display='none'; }
        }

        socket.on('update_prsi', (g) => {
            document.getElementById('msg').innerText = g.msg;
            const top = g.discard[g.discard.length - 1];
            const topBox = document.getElementById('top-card');
            topBox.innerHTML = `<div class="card ${top.suit}">${top.val}<br>${top.suit[0]}</div>`;

            const me = g.players.find(p => p.id === socket.id);
            const handBox = document.getElementById('my-hand');
            handBox.innerHTML = '';
            
            if(me) {
                me.hand.forEach((c, i) => {
                    const div = document.createElement('div');
                    div.className = `card ${c.suit}`;
                    div.innerHTML = `${c.val}<br>${c.suit[0]}`;
                    div.onclick = () => socket.emit('play_card', {idx: i});
                    handBox.appendChild(div);
                });
            }
        });
    </script>
</body>
</html>
"""