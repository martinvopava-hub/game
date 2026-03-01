from flask import Blueprint, render_template
import random

# Definice modulu
kostky_bp = Blueprint('kostky', __name__)

@kostky_bp.route('/kostky')
def kostky_page():
    return render_template('kostky.html')

# Sem přesuneš i pomocné funkce jako vypocitej_body_kostky






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
    # NOVÁ PROMĚNNÁ: Postupka 1-2-3-4-5-6 = 2000 bodů
    if len(counts) == 6:
        return 2000

    for num, count in counts.items():
        if num == 1:
            # Jedničky: 1=100, 11=200, 111=1000, pak zdvojnásobování
            if count < 3:
                body += count * 100
            else:
                zaklad = 1000
                body += zaklad * (2 ** (count - 3))
        elif num == 5:
            # Pětky: 5=50, 55=100, 555=500, pak zdvojnásobování
            if count < 3:
                body += count * 50
            else:
                zaklad = 500
                body += zaklad * (2 ** (count - 3))
        else:
            # Ostatní čísla (2,3,4,6): Pouze trojice a více
            if count >= 3:
                zaklad = num * 100
                body += zaklad * (2 ** (count - 3))
            else:
                # Neplatná kombinace (např. dvě dvojky)
                return 0
    return body

@app.route('/')
def index():
    if 'game' not in session:
        session['game'] = {
            'total': 0, 'turn': 0, 'dice_count': 6,
            'current_roll': [], 'msg': 'Hra připravena. Hoďte si!'
        }
    return render_template_string(HTML_TEMPLATE, g=session['game'])

@app.route('/action', methods=['POST'])
def action():
    g = session.get('game')
    if not g: return redirect(url_for('index'))

    if 'roll_action' in request.form:
        g['current_roll'] = [random.randint(1, 6) for _ in range(g['dice_count'])]
        
        # Kontrola "smrti"
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

@app.route('/reset')
def reset():
    session.pop('game', None)
    return redirect(url_for('index'))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Kostky - Python Flask</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: white; display: flex; justify-content: center; padding-top: 30px; }
        .table { background: #1e3a1e; padding: 30px; border-radius: 20px; box-shadow: 0 0 50px rgba(0,0,0,0.5); width: 480px; border: 8px solid #3e2723; text-align: center; }
        .die { display: inline-block; width: 55px; height: 55px; line-height: 55px; background: white; color: black; font-size: 28px; font-weight: bold; border-radius: 10px; margin: 8px; cursor: pointer; transition: 0.2s; box-shadow: 3px 3px 0 #ccc; }
        .die.selected { transform: translateY(-10px); background: #f1c40f; box-shadow: 0 5px 0 #b7950b; }
        .btn { padding: 12px 20px; font-size: 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; margin: 5px 0; width: 100%; }
        .btn-roll { background: #2ecc71; color: white; }
        .btn-keep { background: #3498db; color: white; }
        .btn-bank { background: #e67e22; color: white; }
        .status { background: rgba(0,0,0,0.4); padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
<div class="table">
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
    <a href="/reset" style="color: #666; font-size: 13px; text-decoration: none; display: block; margin-top: 15px;">Nová hra / Reset</a>
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