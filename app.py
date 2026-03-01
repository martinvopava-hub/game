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



    