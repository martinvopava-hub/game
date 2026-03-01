from flask import Flask, render_template_string, request, session, redirect, url_for
import random

app = Flask(__name__)
app.secret_key = 'tajny_klic_pro_session'

WIN_SCORE = 5000


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


@app.route('/', methods=['GET'])
def index():
    if 'players' not in session:
        return render_template_string(SETUP_TEMPLATE)

    return render_template_string(GAME_TEMPLATE,
                                  players=session['players'],
                                  current=session['current_player'],
                                  game=session['game'],
                                  win_score=WIN_SCORE)


@app.route('/setup', methods=['POST'])
def setup():
    names = request.form.get('players')
    if names:
        player_list = [n.strip() for n in names.split(',') if n.strip()]
        session['players'] = [{'name': n, 'score': 0} for n in player_list]
        session['current_player'] = 0
        session['game'] = {
            'turn': 0,
            'dice_count': 6,
            'current_roll': [],
            'msg': 'Hra připravena. Hoďte si!'
        }
    return redirect(url_for('index'))


@app.route('/action', methods=['POST'])
def action():
    game = session['game']
    players = session['players']
    current = session['current_player']

    if 'roll_action' in request.form:
        game['current_roll'] = [random.randint(1, 6) for _ in range(game['dice_count'])]

        test_counts = {}
        for x in game['current_roll']:
            test_counts[x] = test_counts.get(x, 0) + 1

        mozne_body = 0
        for n, cnt in test_counts.items():
            if n == 1 or n == 5 or cnt >= 3 or len(test_counts) == 6:
                mozne_body += 1

        if mozne_body == 0:
            game['msg'] = f"❌ NULA! {players[current]['name']} ztrácí {game['turn']} bodů."
            game['turn'] = 0
            game['dice_count'] = 6
            game['current_roll'] = []
            session['current_player'] = (current + 1) % len(players)
        else:
            game['msg'] = "Vyberte bodované kostky."

    elif 'keep_action' in request.form:
        indices_str = request.form.get('selected_indices', '')
        if indices_str:
            indices = [int(i) for i in indices_str.split(',')]
            selected_values = [game['current_roll'][i] for i in indices]

            points = vypocitej_vyber(selected_values)
            if points > 0:
                game['turn'] += points
                game['dice_count'] -= len(selected_values)
                if game['dice_count'] == 0:
                    game['dice_count'] = 6
                game['current_roll'] = []
                game['msg'] = f"Získáno {points} bodů."
            else:
                game['msg'] = "⚠️ Neplatný výběr!"

    elif 'bank_action' in request.form:
        if game['turn'] >= 350:
            players[current]['score'] += game['turn']

            if players[current]['score'] >= WIN_SCORE:
                game['msg'] = f"🏆 {players[current]['name']} vyhrál hru!"
            else:
                game['msg'] = f"{players[current]['name']} zapsal {game['turn']} bodů."
                session['current_player'] = (current + 1) % len(players)

            game['turn'] = 0
            game['dice_count'] = 6
            game['current_roll'] = []
        else:
            game['msg'] = "⚠️ Potřebujete alespoň 350 bodů."

    session['game'] = game
    session['players'] = players

    return redirect(url_for('index'))


@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))


# ================= SETUP =================

SETUP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Nastavení hráčů</title>
<style>
body {font-family:Segoe UI;background:#121212;color:white;display:flex;justify-content:center;align-items:center;height:100vh;}
.box {background:#1e3a1e;padding:40px;border-radius:20px;width:400px;text-align:center;}
input {width:100%;padding:12px;border-radius:8px;border:none;margin-top:15px;}
button {margin-top:20px;padding:12px;width:100%;border:none;border-radius:8px;background:#2ecc71;color:white;font-weight:bold;}
</style>
</head>
<body>
<div class="box">
<h2>Zadej hráče (oddělené čárkou)</h2>
<form action="/setup" method="post">
<input type="text" name="players" placeholder="Např: Petr, Jana, Karel" required>
<button type="submit">Spustit hru</button>
</form>
</div>
</body>
</html>
"""


# ================= GAME =================

GAME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Multiplayer Kostky</title>
<style>
body {font-family:Segoe UI;background:#121212;color:white;display:flex;justify-content:center;padding-top:30px;}
.table {background:#1e3a1e;padding:30px;border-radius:20px;width:500px;text-align:center;}
.die {display:inline-block;width:55px;height:55px;line-height:55px;background:white;color:black;font-size:28px;border-radius:10px;margin:8px;cursor:pointer;}
.die.selected {background:#f1c40f;}
.btn {padding:12px;width:100%;margin-top:5px;border:none;border-radius:8px;font-weight:bold;}
.roll {background:#2ecc71;color:white;}
.bank {background:#e67e22;color:white;}
.scoreboard {margin-bottom:15px;text-align:left;}
.active {color:#2ecc71;font-weight:bold;}
</style>
</head>
<body>
<div class="table">

<h3>Hraje: {{ players[current].name }}</h3>

<div class="scoreboard">
{% for p in players %}
<div class="{% if loop.index0 == current %}active{% endif %}">
{{ p.name }}: {{ p.score }}
</div>
{% endfor %}
</div>

<p>{{ game.msg }}</p>

<div>
{% for val in game.current_roll %}
<div class="die" onclick="toggleDie(this, {{ loop.index0 }})">{{ val }}</div>
{% endfor %}
</div>

<form method="post" action="/action" id="game-form">
<input type="hidden" name="selected_indices" id="selected_indices">

{% if not game.current_roll %}
<button name="roll_action" class="btn roll">HODIT ({{ game.dice_count }})</button>
{% else %}
<button type="button" onclick="confirmSelection()" class="btn roll">POTVRDIT VÝBĚR</button>
{% endif %}

{% if game.turn > 0 %}
<button name="bank_action" class="btn bank">ZAPSAT BODY ({{ game.turn }})</button>
{% endif %}
</form>

<br>
<a href="/reset" style="color:#aaa;">Restart celé hry</a>

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
if (selected.length === 0) { alert("Vyber kostky!"); return; }
document.getElementById('selected_indices').value = selected.join(',');
let input = document.createElement("input");
input.type = "hidden";
input.name = "keep_action";
document.getElementById('game-form').appendChild(input);
document.getElementById('game-form').submit();
}
</script>

</body>
</html>
"""


if __name__ == '__main__':
    app.run(debug=True)