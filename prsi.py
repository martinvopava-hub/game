import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from prsi import PrsiGame  # Předpokládá, že máš třídu PrsiGame v souboru prsi.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'prsi-tajny-klic-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Inicializace hry
game = PrsiGame()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/prsi')
def prsi_page():
    return render_template('prsi.html')

# --- SOCKET.IO EVENTY ---

@socketio.on('request_prsi_update')
def handle_update_request():
    emit('update_prsi', game.get_state())

@socketio.on('prsi_play')
def handle_play(data):
    idx = data.get('idx')
    chosen_color = data.get('color') # Barva od Svrška
    
    # Pokus o zahrání karty hráčem
    success = game.play_card(idx, is_player=True, chosen_color=chosen_color)
    
    if success:
        # Pokud hráč vyhodil kartu, pošleme update a pak necháme hrát PC
        game.msg = "Hraje počítač..."
        emit('update_prsi', game.get_state(), broadcast=True)
        
        eventlet.sleep(1.5) # Pauza, aby hráč viděl, co se děje
        pc_logic()
    else:
        # Pokud tah nebyl platný (např. špatná barva), pošleme varování jen hráči
        emit('update_prsi', game.get_state())

@socketio.on('prsi_draw')
def handle_draw():
    # Hráč si líže (nebo stojí/bere trestné karty)
    game.draw(is_player=True)
    emit('update_prsi', game.get_state(), broadcast=True)
    
    eventlet.sleep(1)
    pc_logic()

def pc_logic():
    # Jednoduchá logika pro PC
    state = game.get_state()
    if state['turn'] == 'pc':
        # Zkusíme najít kartu, kterou může PC zahrát
        played = False
        for i in range(len(game.pc_hand)):
            # PC zahraje první možnou kartu (pokud je Svršek, vybere si srdce)
            if game.play_card(i, is_player=False, chosen_color='srdce'):
                played = True
                break
        
        if not played:
            game.draw(is_player=False)
            
        emit('update_prsi', game.get_state(), broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    import random

class PrsiGame:
    def __init__(self):
        self.barvy = ['zalud', 'list', 'srdce', 'koule']
        self.hodnoty = ['7', '8', '9', '10', 'S', 'V', 'K', 'A']
        self.penalty_cards = 0
        self.skip_turn = False
        self.current_color = None
        self.reset()

    def reset(self):
        self.deck = [{'b': b, 'h': h} for b in self.barvy for h in self.hodnoty]
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop() for _ in range(5)]
        self.pc_hand = [self.deck.pop() for _ in range(5)]
        
        # První karta nesmí být speciální
        start_card = self.deck.pop()
        while start_card['h'] in ['7', 'A', 'V']:
            self.deck.insert(0, start_card)
            start_card = self.deck.pop()
            
        self.stack = [start_card]
        self.current_color = start_card['b']
        self.turn = 'player'
        self.msg = "Hra začala! Tvůj tah."

    def get_state(self):
        return {
            'player_hand': self.player_hand,
            'pc_hand_count': len(self.pc_hand),
            'stack_top': self.stack[-1],
            'current_color': self.current_color,
            'penalty': self.penalty_cards,
            'skip': self.skip_turn,
            'turn': self.turn,
            'msg': self.msg
        }

    def play_card(self, idx, is_player=True, chosen_color=None):
        hand = self.player_hand if is_player else self.pc_hand
        card = hand[idx]
        top = self.stack[-1]

        # Logika Sedmičky
        if self.penalty_cards > 0 and card['h'] != '7':
            return False
        # Logika Esa
        if self.skip_turn and card['h'] != 'A':
            return False

        # Základní pravidlo Prší
        if card['h'] == 'V' or card['h'] == top['h'] or card['b'] == self.current_color:
            hand.pop(idx)
            self.stack.append(card)
            self.current_color = chosen_color if chosen_color else card['b']
            
            # Efekty
            if card['h'] == '7': self.penalty_cards += 2
            if card['h'] == 'A': self.skip_turn = True
            
            self.turn = 'pc' if is_player else 'player'
            self.msg = "Hraje " + ("počítač" if is_player else "hráč")
            return True
        return False

    def draw(self, is_player=True):
        hand = self.player_hand if is_player else self.pc_hand
        
        if self.skip_turn:
            self.skip_turn = False
            self.turn = 'pc' if is_player else 'player'
            self.msg = ("Hráč" if is_player else "PC") + " stál (Eso)."
            return True

        if self.penalty_cards > 0:
            for _ in range(self.penalty_cards):
                if self.deck: hand.append(self.deck.pop())
            self.penalty_cards = 0
            self.turn = 'pc' if is_player else 'player'
            return True

        if self.deck:
            hand.append(self.deck.pop())
            self.turn = 'pc' if is_player else 'player'
            return True
        return False