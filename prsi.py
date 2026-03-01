import random

class PrsiGame:
    def __init__(self):
        self.barvy = ['Srdce', 'Kule', 'Zelené', 'Žaludy']
        self.hodnoty = ['7', '8', '9', '10', 'Spodek', 'Svršek', 'Král', 'Eso']
        self.reset()

    def reset(self):
        # Vytvoření balíčku 32 karet
        self.deck = [{'b': b, 'h': h} for b in self.barvy for h in self.hodnoty]
        random.shuffle(self.deck)
        
        # Rozdání karet (4 každému)
        self.player_hand = [self.deck.pop() for _ in range(4)]
        self.pc_hand = [self.deck.pop() for _ in range(4)]
        
        # První karta na stůl (nesmí to být speciální karta pro zjednodušení začátku)
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
            'msg': self.msg,
            'deck_count': len(self.deck),
            'turn': self.turn
        }

    def play_card(self, card_idx):
        if self.turn != 'player': return False
        
        card = self.player_hand[card_idx]
        top = self.stack[-1]

        # Pravidlo: Stejná barva, stejná hodnota nebo Svršek
        if card['b'] == self.current_color or card['h'] == top['h'] or card['h'] == 'Svršek':
            self.stack.append(self.player_hand.pop(card_idx))
            self.current_color = card['b']
            
            if len(self.player_hand) == 0:
                self.msg = "🎉 VYHRÁL JSI!"
                self.turn = 'end'
            else:
                self.turn = 'pc'
                self.msg = "Hraje počítač..."
            return True
        return False

    def pc_turn(self):
        if self.turn != 'pc': return
        
        top = self.stack[-1]
        # Najde kartu, kterou může zahrát
        mozne_indexy = [i for i, c in enumerate(self.pc_hand) 
                        if c['b'] == self.current_color or c['h'] == top['h'] or c['h'] == 'Svršek']
        
        if mozne_indexy:
            idx = mozne_indexy[0]
            karta = self.pc_hand.pop(idx)
            self.stack.append(karta)
            self.current_color = karta['b']
            self.msg = f"Počítač zahrál {karta['h']} {karta['b']}."
        else:
            if self.deck:
                self.pc_hand.append(self.deck.pop())
                self.msg = "Počítač si lízl kartu."
            else:
                self.msg = "Balíček je prázdný, počítač stojí."
        
        if len(self.pc_hand) == 0:
            self.msg = "💀 Prohrál jsi! Počítač je bez karet."
            self.turn = 'end'
        else:
            self.turn = 'player'

    def draw_card(self):
        if self.turn == 'player' and self.deck:
            self.player_hand.append(self.deck.pop())
            self.turn = 'pc'
            self.msg = "Lízl jsi si. Hraje počítač..."
            return True
        return False