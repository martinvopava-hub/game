import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'multi-game-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# =====================================================
# ================= MENU STRÁNKA =====================
# =====================================================

MENU_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Game Hub</title>
<style>
body {
    margin:0;
    font-family:Segoe UI;
    background:#0f0f0f;
    color:white;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    height:100vh;
}
h1 { font-size:48px; margin-bottom:40px; }
.btn {
    padding:20px 60px;
    margin:15px;
    font-size:24px;
    border:none;
    border-radius:15px;
    cursor:pointer;
    transition:0.3s;
}
.kostky { background:#2ecc71; color:white; }
.prsi { background:#3498db; color:white; }
.btn:hover { transform:scale(1.1); }
</style>
</head>
<body>
<h1>🎮 VYBER HRU</h1>
<button class="btn kostky" onclick="location.href='/kostky'">🎲 KOSTKY</button>
<button class="btn prsi" onclick="location.href='/prsi'">🃏 PRŠÍ</button>
</body>
</html>
"""

@app.route('/')
def menu():
    return render_template_string(MENU_HTML)

# =====================================================
# ================= KOSTKY (TVŮJ KÓD) =================
# =====================================================

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

@app.route('/kostky')
def kostky():
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
    game['selected_indices'] = []
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
        next_turn()
    socketio.emit('update', game)

@socketio.on('reset_game')
def handle_reset():
    global game
    game = {
        'players': [],
        'scores': {},
        'turn_index': 0,
        'current_turn_pts': 0,
        'dice_count': 6,
        'current_roll': [],
        'selected_indices': [],
        'msg': 'Restart.',
        'winner': None,
        'finisher_sid': None
    }
    socketio.emit('reload')

# =====================================================
# ================= PRŠÍ (ZATÍM JEN STRÁNKA) =========
# =====================================================

@app.route('/prsi')
def prsi():
    return """
    <html>
    <body style="background:#111;color:white;font-family:Segoe UI;text-align:center;margin-top:100px;">
    <h1>🃏 PRŠÍ</h1>
    <h2>Tady bude druhá hra</h2>
    <br>
    <button onclick="location.href='/'" style="padding:15px 40px;font-size:20px;">Zpět do menu</button>
    </body>
    </html>
    """

# =====================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)