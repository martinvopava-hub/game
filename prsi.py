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