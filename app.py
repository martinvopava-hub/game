import eventlet
eventlet.monkey_patch()

import os
import random
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kostky-tajemstvi-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBÁLNÍ STAV ---
game_state = {
    'players': {},
    'order': [],
    'current_player': None,
    'turn_points': 0,
    'dice_count': 6,
    'current_roll': [],
    'msg': 'Čekám na hráče...',
    'winner': None
}

# --- VÝPOČET BODŮ ---
def vypocitej_vyber(vyber):
    if not vyber: return 0
    counts = {}
    for x in vyber: counts[x] = counts.get(x, 0) + 1
    
    body = 0
    if len(counts) == 6: return 2000

    for num, count in counts.items():
        if num == 1:
            if count < 3: body += count * 100
            else: body += 1000 * (2 ** (count - 3))
        elif num == 5:
            if count < 3: body += count * 50
            else: body += 500 * (2 ** (count - 3))
        else:
            if count >= 3:
                zaklad = num * 100
                body += zaklad * (2 ** (count - 3))
            else: return 0
    return body

def dalsi_hrac():
    if not game_state['order']: return
    idx = game_state['order'].index(game_state['current_player'])
    idx = (idx + 1) % len(game_state['order'])
    game_state['current_player'] = game_state['order'][idx]
    game_state['turn_points'] = 0
    game_state['dice_count'] = 6
    game_state['current_roll'] = []

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# --- SOCKET EVENTS ---

@socketio.on('join_game')
def handle_join(data):
    sid = request.sid
    name = data.get('name')

    if sid not in game_state['players']:
        game_state['players'][sid] = {'name': name, 'total': 0}
        game_state['order'].append(sid)

    if game_state['current_player'] is None:
        game_state['current_player'] = sid
        game_state['msg'] = f"{name} začíná!"

    socketio.emit('update_game', game_state)

@socketio.on('roll_dice')
def handle_roll():
    sid = request.sid
    if sid != game_state['current_player']: return

    game_state['current_roll'] = [random.randint(1, 6) for _ in range(game_state['dice_count'])]

    test_counts = {}
    for x in game_state['current_roll']:
        test_counts[x] = test_counts.get(x, 0) + 1

    mozne_body = any(n == 1 or n == 5 or cnt >= 3 for n, cnt in test_counts.items()) or len(test_counts) == 6

    if not mozne_body:
        game_state['msg'] = f"NULA! Ztráta tahu."
        dalsi_hrac()
    else:
        game_state['msg'] = "Vyber kostky."

    socketio.emit('update_game', game_state)

@socketio.on('keep_dice')
def handle_keep(data):
    sid = request.sid
    if sid != game_state['current_player']: return

    indices = data.get('indices', [])
    selected_values = [game_state['current_roll'][i] for i in indices]
    points = vypocitej_vyber(selected_values)

    if points > 0:
        game_state['turn_points'] += points
        game_state['dice_count'] -= len(selected_values)
        if game_state['dice_count'] == 0:
            game_state['dice_count'] = 6
        game_state['current_roll'] = []
        game_state['msg'] = f"+{points} bodů"
    else:
        game_state['msg'] = "Neplatná kombinace!"

    socketio.emit('update_game', game_state)

@socketio.on('bank_points')
def handle_bank():
    sid = request.sid
    if sid != game_state['current_player']: return

    if game_state['turn_points'] >= 350:
        game_state['players'][sid]['total'] += game_state['turn_points']

        if game_state['players'][sid]['total'] >= 10000:
            game_state['winner'] = game_state['players'][sid]['name']
            game_state['msg'] = f"🏆 {game_state['winner']} vyhrál!"
            socketio.emit('update_game', game_state)
            eventlet.sleep(5)
            reset_game()
            return

        dalsi_hrac()
    else:
        game_state['msg'] = "Minimum 350 bodů."

    socketio.emit('update_game', game_state)

def reset_game():
    for p in game_state['players']:
        game_state['players'][p]['total'] = 0
    game_state['turn_points'] = 0
    game_state['dice_count'] = 6
    game_state['current_roll'] = []
    game_state['winner'] = None
    if game_state['order']:
        game_state['current_player'] = game_state['order'][0]
    socketio.emit('update_game', game_state)

# --- HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Kostky ONLINE</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
<style>
body { font-family:sans-serif; background:#121212; color:white; text-align:center; }
.table { background:#1e3a1e; padding:20px; border-radius:20px; width:500px; margin:40px auto; border:5px solid #3e2723; }
.die { display:inline-block; width:50px; height:50px; line-height:50px; background:white; color:black; margin:5px; border-radius:10px; font-weight:bold; cursor:pointer; font-size:24px; }
.die.selected { background:#f1c40f; }
.btn { width:100%; padding:10px; margin:5px 0; font-weight:bold; cursor:pointer; border-radius:5px; border:none; }
.btn-roll { background:#2ecc71; color:white; }
.btn-keep { background:#3498db; color:white; }
.btn-bank { background:#e67e22; color:white; }
#login { position:fixed; inset:0; background:#000000dd; display:flex; justify-content:center; align-items:center; }
#login-box { background:#222; padding:30px; border-radius:15px; }
</style>
</head>
<body>

<div id="login">
  <div id="login-box">
    <h2>Zadej jméno hráče</h2>
    <input id="playerName" placeholder="Tvoje jméno">
    <button onclick="joinGame()">Vstoupit do hry</button>
  </div>
</div>

<div class="table">
<h2 id="players"></h2>
<h1 id="turnInfo"></h1>
<h3 id="msg"></h3>
<div id="dice"></div>
<div id="controls"></div>
</div>

<script>
const socket = io();
let selected=[];

function joinGame(){
  const name=document.getElementById("playerName").value;
  if(!name) return;
  socket.emit("join_game",{name:name});
  document.getElementById("login").style.display="none";
}

socket.on("update_game",(data)=>{
  let playersText="";
  for(const id in data.players){
    playersText+=data.players[id].name+" ("+data.players[id].total+") | ";
  }
  document.getElementById("players").innerText=playersText;

  const current=data.players[data.current_player];
  document.getElementById("turnInfo").innerText=current?("Hraje: "+current.name+" | Tah: "+data.turn_points):"";

  document.getElementById("msg").innerText=data.msg;

  const diceDiv=document.getElementById("dice");
  diceDiv.innerHTML="";
  data.current_roll.forEach((v,i)=>{
    const d=document.createElement("div");
    d.className="die"+(selected.includes(i)?" selected":"");
    d.innerText=v;
    d.onclick=()=>{ if(selected.includes(i)) selected=selected.filter(x=>x!=i); else selected.push(i); d.classList.toggle("selected"); };
    diceDiv.appendChild(d);
  });

  const ctrl=document.getElementById("controls");
  ctrl.innerHTML="";
  if(data.current_roll.length==0)
    ctrl.innerHTML+=`<button class="btn btn-roll" onclick="socket.emit('roll_dice')">HODIT</button>`;
  else
    ctrl.innerHTML+=`<button class="btn btn-keep" onclick="socket.emit('keep_dice',{indices:selected});selected=[];">POTVRDIT</button>`;

  if(data.turn_points>0)
    ctrl.innerHTML+=`<button class="btn btn-bank" onclick="socket.emit('bank_points')">ZAPSAT</button>`;
});
</script>

</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)