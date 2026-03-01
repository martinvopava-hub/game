import random

# Definice karet
BARVY = ['Srdce', 'Kule', 'Zelené', 'Žaludy']
HODNOTY = ['7', '8', '9', '10', 'Spodek', 'Svršek', 'Král', 'Eso']

def vytvor_balicek():
    return [{'barva': b, 'hodnota': h} for b in BARVY for h in HODNOTY]

def format_karta(karta):
    return f"{karta['barva']} {karta['hodnota']}"

def hraj_prsi():
    balicek = vytvor_balicek()
    random.shuffle(balicek)

    hrac = [balicek.pop() for _ in range(4)]
    pocitac = [balicek.pop() for _ in range(4)]
    odhazovaci_balicek = [balicek.pop()]
    
    aktualni_barva = odhazovaci_balicek[-1]['barva']
    trestne_karty = 0
    stojis = False

    while len(hrac) > 0 and len(pocitac) > 0:
        horni_karta = odhazovaci_balicek[-1]
        print(f"\n--- Na stole je: {format_karta(horni_karta)} (Hledaná barva: {aktualni_barva}) ---")
        
        # --- TAH HRÁČE ---
        print(f"Vaše karty: {', '.join([f'[{i}] {format_karta(k)}' for i, k in enumerate(hrac)])}")
        
        mozne_karty = [i for i, k in enumerate(hrac) if k['barva'] == aktualni_barva or k['hodnota'] == horni_karta['hodnota'] or k['hodnota'] == 'Svršek']
        
        volba = input("Vyberte číslo karty nebo 'l' pro líznutí: ")
        
        if volba.lower() == 'l':
            hrac.append(balicek.pop())
            print("Lízl jste si kartu.")
        else:
            index = int(volba)
            vybrana_karta = hrac.pop(index)
            odhazovaci_balicek.append(vybrana_karta)
            aktualni_barva = vybrana_karta['barva']
            
            if vybrana_karta['hodnota'] == 'Svršek':
                print("0: Srdce, 1: Kule, 2: Zelené, 3: Žaludy")
                nova_b = int(input("Vyberte novou barvu (0-3): "))
                aktualni_barva = BARVY[nova_b]
        
        if len(hrac) == 0: break

        # --- TAH POČÍTAČE (Zjednodušený) ---
        input("\n(Stiskněte Enter pro tah počítače...)")
        moznosti_pc = [i for i, k in enumerate(pocitac) if k['barva'] == aktualni_barva or k['hodnota'] == horni_karta['hodnota'] or k['hodnota'] == 'Svršek']
        
        if moznosti_pc:
            karta_pc = pocitac.pop(moznosti_pc[0])
            odhazovaci_balicek.append(karta_pc)
            aktualni_barva = karta_pc['barva']
            print(f"Počítač zahrál: {format_karta(karta_pc)}")
            if karta_pc['hodnota'] == 'Svršek':
                aktualni_barva = random.choice(BARVY)
                print(f"Počítač změnil barvu na: {aktualni_barva}")
        else:
            pocitac.append(balicek.pop())
            print("Počítač si lízl kartu.")

    print("\nKONEC HRY!")
    print("Vyhrál jsi!" if len(hrac) == 0 else "Vyhrál počítač!")

if __name__ == "__main__":
    hraj_prsi()