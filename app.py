from flask import Flask, render_template_string, request, session, redirect, url_for
import random

app = Flask(__name__)
app.secret_key = 'tajny_klic_pro_session'


# ================= VÝPOČET BODŮ =================

def vypocitej_vyber(vyber):
    if not vyber:
        return 0

    counts = {}
    for x in vyber:
        counts[x] = counts.get(x, 0) + 1

    if len(counts) == 6:
        return 2000

    body = 0
    for num, count in counts.items():
        if num == 1:
            body += count * 100 if count < 3 else 1000 * (2 ** (count - 3))
        elif num == 5:
            body += count * 50 if count < 3 else 500 * (2 ** (count - 3))
        else:
            if count >= 3:
                body += (num * 100) * (2 ** (count - 3))
            else:
                return 0
    return body


# ================= HLAVNÍ ROUTA =================

@app.route('/')
def index():
    if 'game' not in session:
        return render_template_string(LOGIN_TEMPLATE)

    g = session['game']
    player = g['players'][g['current_player']]

    return render_template_string(HTML_TEMPLATE, g=g, player=player)


# ================= LOGIN - VÍCE HRÁČŮ =================

@app.route('/login', methods=['POST'])
def login():
    names = request.form.get('nicknames')
    if not names:
        return redirect(url_for('index'))

    players = []
    for name in names.split(','):
        name = name.strip()
        if name:
            players.append({'name': name, 'score': 0})

    session['game'] = {
        'players': players,
        'current_player': 0,
        'turn': 0,
        'dice_count': 6,
        'current_roll': [],
        'msg': 'Hra začíná!',
        'final_round': False,
        'final_index': None
    }

    return redirect(url_for('index'))


# ================= AKCE =================

@app.route('/action', methods=['POST'])
def action():
    g = session['game']
    current = g['players'][g['current_player']]

    # HOD
    if 'roll_action' in request.form:
        g['current_roll'] = [random.randint(1, 6) for _ in range(g['dice_count'])]

        test_counts = {}
        for x in g['current_roll']:
            test_counts[x] = test_counts.get(x, 0) + 1

        if not any(n == 1 or n == 5 or c >= 3 or len(test_counts) == 6
                   for n, c in test_counts.items()):
            g['msg'] = f"❌ NULA! {current['name']} ztrácí {g['turn']} bodů."
            g['turn'] = 0
            g['dice_count'] = 6
            g['current_roll'] = []
        else:
            g['msg'] = "Vyberte bodované kostky."

    # POTVRZENÍ
    elif 'keep_action' in request.form:
        indices_str = request.form.get('selected_indices', '')
        if indices_str:
            indices = [int(i) for i in indices_str.split(',')]
            selected = [g['current_roll'][i] for i in indices]

            points = vypocitej_vyber(selected)
            if points > 0:
                g['turn'] += points
                g['dice_count'] -= len(selected)
                if g['dice_count'] == 0:
                    g['dice_count'] = 6
                g['current_roll'] = []
                g['msg'] = f"{current['name']} získal {points} bodů."
            else:
                g['msg'] = "⚠️ Neplatná kombinace."

    # ZAPSÁNÍ KOLA
    elif 'bank_action' in request.form:
        if g['turn'] >= 350:
            current['score'] += g['turn']
            g['msg'] = f"{current['name']} zapsal {g['turn']} bodů!"
            g['turn'] = 0
            g['dice_count'] = 6
            g['current_roll'] = []

            # Spuštění finálního kola
            if current['score'] >= 10000 and not g['final_round']:
                g['final_round'] = True
                g['final_index'] = g['current_player']
                g['msg'] += " 🔥 Finální kolo!"

            # Posun hráče
            g['current_player'] = (g['current_player'] + 1) % len(g['players'])

            # Konec hry po finálním kole
            if g['final_round'] and g['current_player'] == g['final_index']:
                winner = max(g['players'], key=lambda p: p['score'])
                g['msg'] = f"🏆 Vítěz je {winner['name']} s {winner['score']} body!"
                g['final_round'] = False

        else:
            g['msg'] = "⚠️ Potřebujete aspoň 350 bodů."

    session['game'] = g
    return redirect(url_for('index'))


@app.route('/reset')
def reset():
    session.pop('game', None)
    return redirect(url_for('index'))


# ================= LOGIN TEMPLATE =================

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Více hráčů</title>
<style>
body { font-family: 'Segoe UI'; background:#121212; color:white; display:flex; justify-content:center; align-items:center; height:100vh;}
.login-box { background:#1e3a1e; padding:40px; border-radius:20px; width:400px; text-align:center;}
input { width:100%; padding:12px; border-radius:8px; border:none; margin-top:15px; font-size:16px;}
button { margin-top:20px; padding:12px; width:100%; border:none; border-radius:8px; background:#2ecc71; color:white; font-weight:bold; font-size:16px; cursor:pointer;}
</style>
</head>
<body>
<div class="login-box">
<h2>Zadej hráče (oddělit čárkou)</h2>
<form action="/login" method="post">
<input type="text" name="nicknames" placeholder="Pepa, Karel, Lucka" required>
<button type="submit">Spustit hru</button>
</form>
</div>
</body>
</html>
"""


# ================= GAME TEMPLATE =================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Kostky - Multiplayer</title>
<style>
body { font-family: 'Segoe UI'; background: #121212; color: white; display: flex; justify-content: center; padding-top: 30px; }
.table { background: #1e3a1e; padding: 30px; border-radius: 20px; box-shadow: 0 0 50px rgba(0,0,0,0.5); width: 480px; border: 8px solid #3e2723; text-align: center; }
.player { font-size:14px; color:#aaa; margin-bottom:10px;}
.die { display:inline-block; width:55px; height:55px; line-height:55px; background:white; color:black; font-size:28px; font-weight:bold; border-radius:10px; margin:8px; cursor:pointer; }
.btn { padding:12px; font-size:16px; border-radius:8px; border:none; cursor:pointer; font-weight:bold; margin:5px 0; width:100%; }
.btn-roll { background:#2ecc71; color:white; }
.btn-keep { background:#3498db; color:white; }
.btn-bank { background:#e67e22; color:white; }
.status { background:rgba(0,0,0,0.4); padding:15px; border-radius:10px; margin-bottom:20px; }
</style>
</head>
<body>
<div class="table">

<div class="player">
Na tahu: <strong>{{ player.name }}</strong>
</div>

<div class="status">
{% for p in g.players %}
<div>{{ p.name }}: {{ p.score }}</div>
{% endfor %}
<div style="margin-top:10px; color:#2ecc71;">V tahu body: {{ g.turn }}</div>
</div>

<p style="min-height:45px; color:#f1c40f;">{{ g.msg }}</p>

<div>
{% for val in g.current_roll %}
<div class="die" onclick="toggleDie(this, {{ loop.index0 }})">{{ val }}</div>
{% endfor %}
</div>

<form action="/action" method="post" id="game-form">
<input type="hidden" name="selected_indices" id="selected_indices">
{% if not g.current_roll %}
<button type="submit" name="roll_action" class="btn btn-roll">HODIT ({{ g.dice_count }})</button>
{% else %}
<button type="button" onclick="confirmSelection()" class="btn btn-keep">POTVRDIT</button>
{% endif %}
{% if g.turn > 0 %}
<button type="submit" name="bank_action" class="btn btn-bank">ZAPSAT BODY</button>
{% endif %}
</form>

</div>

<script>
let selected = [];
function toggleDie(el, idx){
el.classList.toggle('selected');
if(selected.includes(idx)){selected=selected.filter(i=>i!==idx);}
else{selected.push(idx);}
}
function confirmSelection(){
document.getElementById('selected_indices').value=selected.join(',');
let input=document.createElement("input");
input.type="hidden";input.name="keep_action";
document.getElementById('game-form').appendChild(input);
document.getElementById('game-form').submit();
}
</script>

</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True)