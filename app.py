from flask import Flask, render_template_string, request, session, redirect, url_for
import random

app = Flask(__name__)
app.secret_key = 'tajny_klic_pro_session'


def vypocitej_vyber(vyber):
    if not vyber:
        return 0
    
    counts = {}
    for x in vyber:
        counts[x] = counts.get(x, 0) + 1
    
    body = 0

    if len(counts) == 6:
        return 2000

    for num, count in counts.items():
        if num == 1:
            if count < 3:
                body += count * 100
            else:
                body += 1000 * (2 ** (count - 3))
        elif num == 5:
            if count < 3:
                body += count * 50
            else:
                body += 500 * (2 ** (count - 3))
        else:
            if count >= 3:
                body += (num * 100) * (2 ** (count - 3))
            else:
                return 0
    return body


@app.route('/')
def index():
    if 'player' not in session:
        return render_template_string(LOGIN_TEMPLATE)

    if 'game' not in session:
        session['game'] = {
            'total': 0, 'turn': 0, 'dice_count': 6,
            'current_roll': [], 'msg': 'Hra připravena. Hoďte si!'
        }

    return render_template_string(HTML_TEMPLATE, g=session['game'], player=session['player'])


@app.route('/login', methods=['POST'])
def login():
    nickname = request.form.get('nickname')
    if nickname:
        session['player'] = nickname
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('player', None)
    session.pop('game', None)
    return redirect(url_for('index'))


@app.route('/reset')
def reset():
    session.pop('game', None)
    return redirect(url_for('index'))


@app.route('/action', methods=['POST'])
def action():
    g = session.get('game')
    if not g:
        return redirect(url_for('index'))

    if 'roll_action' in request.form:
        g['current_roll'] = [random.randint(1, 6) for _ in range(g['dice_count'])]

        test_counts = {}
        for x in g['current_roll']:
            test_counts[x] = test_counts.get(x, 0) + 1

        mozne_body = 0
        for n, cnt in test_counts.items():
            if n == 1 or n == 5 or cnt >= 3 or len(test_counts) == 6:
                mozne_body += 1

        if mozne_body == 0:
            g['msg'] = f"❌ NULA! Nic nepadlo. Ztrácíte {g['turn']} bodů."
            g['turn'] = 0
            g['dice_count'] = 6
            g['current_roll'] = []
        else:
            g['msg'] = "Vyberte bodované kostky."

    elif 'keep_action' in request.form:
        indices_str = request.form.get('selected_indices', '')
        if indices_str:
            indices = [int(i) for i in indices_str.split(',')]
            selected_values = [g['current_roll'][i] for i in indices]

            points = vypocitej_vyber(selected_values)
            if points > 0:
                g['turn'] += points
                g['dice_count'] -= len(selected_values)
                if g['dice_count'] == 0:
                    g['dice_count'] = 6
                g['current_roll'] = []
                g['msg'] = f"Získáno {points} bodů. Celkem v tahu: {g['turn']}."
            else:
                g['msg'] = "⚠️ Neplatný výběr kombinace!"

    elif 'bank_action' in request.form:
        if g['turn'] >= 350:
            g['total'] += g['turn']
            g['msg'] = f"💰 Zapsáno {g['turn']} bodů."
            g['turn'] = 0
            g['dice_count'] = 6
            g['current_roll'] = []
        else:
            g['msg'] = "⚠️ Pro zápis musíte mít aspoň 350 bodů!"

    session['game'] = g
    return redirect(url_for('index'))


# ================= LOGIN =================

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Přihlášení hráče</title>
<style>
body { font-family: 'Segoe UI'; background:#121212; color:white; display:flex; justify-content:center; align-items:center; height:100vh;}
.login-box { background:#1e3a1e; padding:40px; border-radius:20px; width:350px; text-align:center;}
input { width:100%; padding:12px; border-radius:8px; border:none; margin-top:15px; font-size:16px;}
button { margin-top:20px; padding:12px; width:100%; border:none; border-radius:8px; background:#2ecc71; color:white; font-weight:bold; font-size:16px; cursor:pointer;}
</style>
</head>
<body>
<div class="login-box">
<h2>Zadej přezdívku</h2>
<form action="/login" method="post">
<input type="text" name="nickname" placeholder="Tvoje jméno" required>
<button type="submit">Hrát</button>
</form>
</div>
</body>
</html>
"""


# ================= GAME =================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Kostky - Python Flask</title>
<style>
body { font-family: 'Segoe UI'; background: #121212; color: white; display: flex; justify-content: center; padding-top: 30px; }
.table { background: #1e3a1e; padding: 30px; border-radius: 20px; box-shadow: 0 0 50px rgba(0,0,0,0.5); width: 480px; border: 8px solid #3e2723; text-align: center; }
.player { font-size:14px; color:#aaa; margin-bottom:10px;}
.die { display: inline-block; width: 55px; height: 55px; line-height: 55px; background: white; color: black; font-size: 28px; font-weight: bold; border-radius: 10px; margin: 8px; cursor: pointer; transition: 0.2s; box-shadow: 3px 3px 0 #ccc; }
.die.selected { transform: translateY(-10px); background: #f1c40f; box-shadow: 0 5px 0 #b7950b; }
.btn { padding: 12px 20px; font-size: 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; margin: 5px 0; width: 100%; }
.btn-roll { background: #2ecc71; color: white; }
.btn-keep { background: #3498db; color: white; }
.btn-bank { background: #e67e22; color: white; }
.btn-danger { background:#c0392b; color:white;}
.btn-gray { background:#555; color:white;}
.status { background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; margin-bottom: 20px; }
.bottom-buttons { margin-top:20px; }
</style>
</head>
<body>
<div class="table">

<div class="player">
Hraje: <strong>{{ player }}</strong>
</div>

<div class="status">
<div style="font-size: 14px; color: #aaa;">CELKOVÉ SKÓRE</div>
<div style="font-size: 36px; font-weight: bold;">{{ "{:,}".format(g.total) }}</div>
<div style="margin-top: 10px; color: #2ecc71; font-size: 18px;">V tahu: <strong>{{ g.turn }}</strong></div>
</div>

<p style="min-height: 45px; color: #f1c40f;">{{ g.msg }}</p>

<div id="dice-container" style="min-height: 80px;">
{% for val in g.current_roll %}
<div class="die" onclick="toggleDie(this, {{ loop.index0 }})">{{ val }}</div>
{% endfor %}
</div>

<form action="/action" method="post" id="game-form">
<input type="hidden" name="selected_indices" id="selected_indices">
{% if not g.current_roll %}
<button type="submit" name="roll_action" class="btn btn-roll">HODIT KOSTKAMI ({{ g.dice_count }})</button>
{% else %}
<button type="button" onclick="confirmSelection()" class="btn btn-keep">POTVRDIT VÝBĚR</button>
{% endif %}
{% if g.turn > 0 %}
<button type="submit" name="bank_action" class="btn btn-bank">UKONČIT KOLO A ZAPSAT</button>
{% endif %}
</form>

<div class="bottom-buttons">
<a href="/reset"><button class="btn btn-gray">🔄 Restart hry</button></a>
<a href="/logout"><button class="btn btn-danger">🚪 Odhlásit</button></a>
</div>

</div>

<script>
let selected = [];
function toggleDie(el, idx) {
el.classList.toggle('selected');
if (selected.includes(idx)) {
selected = selected.filter(i => i !== idx);
} else {
selected.push(idx);
}
}
function confirmSelection() {
if (selected.length === 0) {
alert("Musíte vybrat aspoň jednu kostku!");
return;
}
document.getElementById('selected_indices').value = selected.join(',');
let input = document.createElement("input");
input.type = "hidden"; input.name = "keep_action";
document.getElementById('game-form').appendChild(input);
document.getElementById('game-form').submit();
}
</script>

</body>
</html>
"""


if __name__ == '__main__':
    app.run(debug=True)