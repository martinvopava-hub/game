import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'herni-server-2026'
# Důležité: cors_allowed_origins="*" povolí připojení z adresy Renderu
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- STAV HRY KOSTKY ---
game = {
    'players': [], 
    'scores': {}, 
    'turn_index': 0, 
    'current_turn_pts': 0,
    'dice_count': 6,
    'current_roll': [],
    'selected_indices': [],
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

# --- ROUTY ---
@app.route('/')
def menu():
    return render_template('index.html')

@app.route('/kostky')
def kostky():
    return render_template('kostky.html')

# --- SOCKET.IO KOSTKY ---
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
    if not game['players'] or game['players'][game['turn_index']]['id'] != sid: return
    game['selected_indices'] = []
    game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]
    
    # Kontrola nuly
    c = {x: game['current_roll'].count(x) for x in set(game['current_roll'])}
    možné = any(n in [1, 5] or cnt >= 3 for n, cnt in c.items()) or len(c) == 6
    if not možné:
        game['msg'] = f"❌ {game['players'][game['turn_index']]['name']} hodil NULU!"
        game['current_turn_pts'] = 0
        game['dice_count'] = 6
        game['current_roll'] = []
        game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    socketio.emit('update', game)

@socketio.on('select_die')
def handle_select(data):
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
    vyber = [game['current_roll'][i] for i in game['selected_indices']]
    body = vypocitej_body(vyber)
    if body > 0:
        game['current_turn_pts'] += body
        game['dice_count'] -= len(game['selected_indices'])
        if game['dice_count'] == 0: game['dice_count'] = 6
        game['current_roll'] = []
        game['selected_indices'] = []
        game['msg'] = f"Zatím nahráno {game['current_turn_pts']} bodů."
    socketio.emit('update', game)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    if game['current_turn_pts'] < 350: return
    game['scores'][sid] += game['current_turn_pts']
    game['current_turn_pts'] = 0
    game['dice_count'] = 6
    game['current_roll'] = []
    game['turn_index'] = (game['turn_index'] + 1) % len(game['players'])
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {'players': [], 'scores': {}, 'turn_index': 0, 'current_turn_pts': 0, 'dice_count': 6, 'current_roll': [], 'selected_indices': [], 'msg': 'Hra restartována.', 'winner': None}
    socketio.emit('reload')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)