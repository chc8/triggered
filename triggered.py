import socket
import threading
import json
import time
import random
import sys
import os

# --- Game Constants and Logic ---
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
TRIGGER_WINDOW = 5.0  

AI_NAMES_POOL = ['Mecha-Wyatt', 'Cyber-Doc', 'Holo-Jesse', 'Robo-Calamity', 'Synth-Billy', 'Auto-Annie', 'Bot-Cassidy', 'Gear-Wayne']

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def create_deck():
    return [{'suit': s, 'value': v, 'rank': r} for s in SUITS for v, r in VALUES.items()]

def calculate_thumper(age, height, weight):
    return round(age + height + weight, 1)

def print_instructions():
    print(r"""
                 _.-'~~~~~~`-._
               /`              `\
              /                  \
             |________....________|
             `---.|.------.|.---`
                  |  _    _  |
                  | |O|  |O| |
                  | '--''--' |
                  |  ,-..-,  |
                  |  '----'  |
                  '.________.'
                    |      |
                  _.|      |._
                /`  |______|  `\
               /                \
    """)
    print(r"""
      _______   _                               _ 
     |__   __| (_)                             | |
        | |_ __ _  __ _  __ _  ___ _ __ ___  __| |
        | | '__| |/ _` |/ _` |/ _ \ '__/ _ \/ _` |
        | | |  | | (_| | (_| |  __/ | |  __/ (_| |
        |_|_|  |_|\__, |\__, |\___|_|  \___|\__,_|
                   __/ | __/ |                    
                  |___/ |___/                     
    """)
    print("="*55)
    print(" "*10 + "HOW TO SURVIVE THE STANDOFF")
    print("="*55)
    print("1. Goal: Collect the most cards, partner.")
    print("2. A 'Bullseye' card is dealt face-up. Everyone gets a face-down card.")
    print("3. When the dealer yells 'CLICK CLICK', cards are flipped.")
    print("4. QUICK DRAW: If you see ANY match to the Bullseye, type 't' and press ENTER!")
    print("   (You got 5 seconds to react before the dust settles).")
    print("5. If there ain't no match, the highest card takes the pot automatically.")
    print("6. MISFIRE: If you type 't' when there's no match, you lose the round!")
    print("7. The dealer always wins a tie. House rules.")
    print("8. DEALER PENALTY: If the dealer misfires, the cards are scattered to the others!")
    print("="*55 + "\n")
    input("Press ENTER when you've read the rules and are ready to ride...")

# --- Network Server ---
class TriggeredServer:
    def __init__(self, port, ai_count):
        self.port = port
        self.ai_count = ai_count
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.clients = {}  
        self.players = []  
        self.lock = threading.RLock() 
        self.trigger_calls = [] 
        self.game_active = False
        self.ai_added = False
        self.round_num = 1
        self.trigger_phase = False 
        
    def start(self):
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(8)
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def register_trigger(self, player_name):
        with self.lock:
            if self.trigger_phase:
                if not any(name == player_name for t, name in self.trigger_calls):
                    self.trigger_calls.append((time.time(), player_name))
                    self.broadcast({'msg': f"  [!] *BANG* {player_name} reached for their iron!"})
            elif self.game_active:
                self.broadcast({'msg': f"  [-] *Click* {player_name} drew too early! (Wait for 'CLICK CLICK')"})

    def handle_client(self, conn):
        try:
            data = conn.recv(1024).decode()
            if data:
                player_info = json.loads(data)
                player_info['conn'] = conn
                player_info['is_ai'] = False
                player_info['score'] = 0
                with self.lock:
                    self.clients[conn] = player_info
                    self.players.append(player_info)
                self.broadcast({'msg': f"Gunslinger {player_info['name']} moseyed into the saloon!"})
                
            buffer = ""
            while True:
                data = conn.recv(1024).decode()
                if not data: break
                buffer += data
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line: continue
                    
                    try:
                        parsed = json.loads(line)
                        action = parsed.get('action')
                        
                        if action == 'trigger' and self.game_active:
                            self.register_trigger(player_info['name'])
                        elif action == 'start' and not self.game_active:
                            threading.Thread(target=self.start_game_logic, daemon=True).start()
                        elif action == 'restart' and not self.game_active:
                            threading.Thread(target=self.start_game_logic, daemon=True).start()
                        elif action == 'exit':
                            self.broadcast({'action': 'quit', 'msg': "\nServer is packin' up. Happy trails, partners!"})
                            time.sleep(1)
                            os._exit(0) 
                    except Exception:
                        pass 
        except:
            pass
        finally:
            if conn in self.clients:
                del self.clients[conn]
            conn.close()

    def broadcast(self, message):
        msg_str = json.dumps(message) + "\n"
        with self.lock:
            for conn in list(self.clients.keys()):
                try:
                    conn.sendall(msg_str.encode())
                    time.sleep(0.01) 
                except:
                    pass

    def start_game_logic(self):
        with self.lock:
            if self.game_active: return
            
            if not self.ai_added:
                available_ai_names = random.sample(AI_NAMES_POOL, min(self.ai_count, len(AI_NAMES_POOL)))
                for i in range(self.ai_count):
                    ai_player = {
                        'name': available_ai_names[i] if i < len(available_ai_names) else f"Bot-{i}",
                        'thumper': round(random.uniform(90.0, 220.0), 1), 
                        'is_ai': True,
                        'score': 0
                    }
                    self.players.append(ai_player)
                self.ai_added = True

            if len(self.players) < 2:
                self.broadcast({'msg': "Hold yer horses! We need at least 2 gunslingers to start."})
                return
                
            self.game_active = True
            self.round_num = 1
            for p in self.players:
                p['score'] = 0

        self.broadcast({'msg': "\n" + "="*40 + "\nDRAW YOUR WEAPONS! THE GAME BEGINS!\n" + "="*40})
        
        thumper_display = "\n--- THUMPER POWERS ---\n"
        for p in self.players:
            thumper_display += f"  {p['name']}: {p['thumper']}\n"
        thumper_display += "----------------------"
        self.broadcast({'msg': thumper_display})
        time.sleep(4)

        self.broadcast({'msg': "\nJudgin' the First Dealer based on Thumper Power..."})
        max_thumper = max(p['thumper'] for p in self.players)
        tied_players = [p for p in self.players if p['thumper'] == max_thumper]
        
        if len(tied_players) > 1:
            self.broadcast({'msg': "We got ourselves a Mexican standoff! Resolvin' the tie..."})
            time.sleep(2)
            first_dealer = random.choice(tied_players)
        else:
            first_dealer = tied_players[0]
            
        self.broadcast({'msg': f"The First Dealer is {first_dealer['name']}!"})
        time.sleep(2)
        
        self.game_loop(first_dealer)

    def evaluate_high_card(self, round_cards, dealer):
        max_rank = max(c['rank'] for c in round_cards.values())
        high_players = [name for name, c in round_cards.items() if c['rank'] == max_rank]
        
        if len(high_players) > 1:
            self.broadcast({'msg': f"Tie for the high card! Dealer {dealer['name']} takes the pot."})
            return dealer
        else:
            winner_name = high_players[0]
            self.broadcast({'msg': f"{winner_name} holds the highest card!"})
            return next(p for p in self.players if p['name'] == winner_name)

    def game_loop(self, first_dealer):
        deck = create_deck()
        random.shuffle(deck)
        
        dealer_idx = self.players.index(first_dealer)
        original_dealer = first_dealer['name']
        
        while len(deck) >= len(self.players) + 1:
            dealer = self.players[dealer_idx]
            self.broadcast({'msg': f"\n--- ROUND {self.round_num} --- Dealer {dealer['name']} is shufflin'..."})
            time.sleep(1.5)
            
            round_cards = {}
            for p in self.players:
                round_cards[p['name']] = deck.pop()
            bullseye = deck.pop()
            
            self.broadcast({'msg': f"Cards dealt face down in the dirt. The Bullseye is:"})
            self.broadcast({'msg': f"\n      >>> {bullseye['value']} of {bullseye['suit']} <<<\n"})
            
            time.sleep(2)
            
            with self.lock:
                self.trigger_calls.clear()
                self.trigger_phase = True
                
            self.broadcast({'msg': f"{dealer['name']} draws and yells: 'CLICK CLICK'! (Turn 'em over!)"})
            
            cards_display = "Cards revealed on the table:\n" + "\n".join([f"  - {name}: {c['value']} of {c['suit']}" for name, c in round_cards.items()])
            self.broadcast({'msg': cards_display})
            
            match_exists = any(c['value'] == bullseye['value'] for c in round_cards.values())
            pot = len(self.players) + 1
            winner = None

            if match_exists:
                for p in self.players:
                    if p['is_ai']:
                        reaction = random.uniform(0.8, 4.8)
                        threading.Timer(reaction, self.register_trigger, args=(p['name'],)).start()

                time.sleep(TRIGGER_WINDOW)
                
                with self.lock:
                    self.trigger_phase = False 
                    
                    if self.trigger_calls:
                        self.trigger_calls.sort(key=lambda x: x[0])
                        fastest_time = self.trigger_calls[0][0]
                        ties = [name for t, name in self.trigger_calls if t - fastest_time < 0.1]
                        
                        if len(ties) > 1:
                            self.broadcast({'msg': f"Trigger TIE between {', '.join(ties)}! Dealer {dealer['name']} breaks the tie and wins."})
                            winner = dealer
                        else:
                            winner_name = ties[0]
                            self.broadcast({'msg': f"*** {winner_name} WAS THE FASTEST GUN! ***"})
                            winner = next(p for p in self.players if p['name'] == winner_name)
                    else:
                        self.broadcast({'msg': "Nobody pulled the trigger! Let's see who's holdin' the high card..."})
                        winner = self.evaluate_high_card(round_cards, dealer)
            else:
                time.sleep(3.0) 
                
                with self.lock:
                    self.trigger_phase = False
                    if self.trigger_calls:
                        self.trigger_calls.sort(key=lambda x: x[0])
                        first_trigger_name = self.trigger_calls[0][1]
                        
                        if first_trigger_name == dealer['name']:
                            self.broadcast({'msg': f"Misfire! The Dealer ({dealer['name']}) drew on a ghost!"})
                            self.broadcast({'msg': f"The dealer loses! {pot} cards are scattered randomly to the other players."})
                            other_players = [p for p in self.players if p['name'] != dealer['name']]
                            if other_players:
                                for _ in range(pot):
                                    random.choice(other_players)['score'] += 1
                            winner = None # No single winner to assign the pot to
                        else:
                            self.broadcast({'msg': f"Misfire! {first_trigger_name} got trigger-happy with no match. Dealer {dealer['name']} takes the pot."})
                            winner = dealer
                    else:
                        winner = self.evaluate_high_card(round_cards, dealer)

            if winner:
                winner['score'] += pot
                self.broadcast({'msg': f"{winner['name']} wins the round and collects {pot} cards!\n"})
            else:
                self.broadcast({'msg': "The round ends in chaos! Cards distributed.\n"})
            
            self.round_num += 1
            dealer_idx = (dealer_idx + 1) % len(self.players)
            time.sleep(2.5)

        self.broadcast({'msg': "\n=== GAME OVER! The deck ran dry. ==="})
        remaining = len(deck)
        first_dealer_obj = next(p for p in self.players if p['name'] == original_dealer)
        first_dealer_obj['score'] += remaining
        self.broadcast({'msg': f"First dealer {original_dealer} pockets the remaining {remaining} cards."})
        
        self.players.sort(key=lambda x: x['score'], reverse=True)
        standings = "\nFINAL BOUNTIES (Scores):\n" + "\n".join([f"  {p['name']}: {p['score']} cards" for p in self.players])
        self.broadcast({'msg': standings})
        
        self.game_active = False
        self.broadcast({'msg': "\nType 'restart' to play a new game, or 'exit' to ride off into the sunset."})

# --- Network Client ---
class TriggeredClient:
    def __init__(self, host, port, name, thumper):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.name = name
        self.thumper = thumper

    def start(self):
        print_instructions()
        
        try:
            self.client_socket.connect((self.host, self.port))
            info = json.dumps({'name': self.name, 'thumper': self.thumper})
            self.client_socket.sendall(info.encode())
            print("\nConnected to the saloon! If you are the Host, type 'start' and press ENTER to begin.\n")
        except ConnectionRefusedError:
            print("Couldn't find the saloon. Make sure the Host has started the server.")
            sys.exit()
            
        threading.Thread(target=self.receive_messages, daemon=True).start()
        
        while True:
            cmd = input().strip()
            if cmd.lower() == 't':
                print(">>> Trigger command sent! <<<") 
                msg = json.dumps({'action': 'trigger'}) + "\n"
                self.client_socket.sendall(msg.encode())
            elif cmd.lower() in ['start', 'restart', 'exit']:
                msg = json.dumps({'action': cmd.lower()}) + "\n"
                self.client_socket.sendall(msg.encode())

    def receive_messages(self):
        buffer = ""
        while True:
            try:
                data = self.client_socket.recv(2048).decode()
                if not data: break
                buffer += data
                
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line: continue
                    
                    try:
                        msg = json.loads(line)
                        if 'msg' in msg:
                            print(msg['msg'])
                        if msg.get('action') == 'quit':
                            time.sleep(0.5)
                            os._exit(0)
                    except Exception:
                        pass
            except:
                print("Disconnected from the server.")
                os._exit(0)

# --- Main Entry Point ---
if __name__ == "__main__":
    print("Welcome to TRIGGERED, partner!")
    mode = input("Start as (S)erver/Host or (C)lient? ").strip().lower()
    
    name = input("Enter your gunslinger name: ")
    
    try:
        age = float(input("Enter your age: "))
        height = float(input("Enter your height (feet): "))
        weight = float(input("Enter your weight (kg): "))
    except ValueError:
        print("Invalid input for stats. Defaulting to average stats.")
        age, height, weight = 30.0, 5.8, 70.0
        
    thumper = calculate_thumper(age, height, weight)
    print(f"Your Thumper Power is: {thumper}\n")

    if mode == 's':
        while True:
            try:
                ai_count = int(input("How many AI players? (0-7): "))
                if 0 <= ai_count <= 7: break
                print("Please enter a number between 0 and 7.")
            except ValueError:
                print("Invalid input.")
                
        port = int(input("Port to host on (e.g., 5555): "))
        
        local_ip = get_local_ip()
        print("\n" + "="*50)
        print(" SERVER UP AND RUNNING!")
        print(f" Tell your partners to connect to IP: {local_ip}")
        print(f" And use Port: {port}")
        print("="*50 + "\n")
        
        server = TriggeredServer(port, ai_count)
        server.start()
        time.sleep(1) 
        
        client = TriggeredClient('127.0.0.1', port, name, thumper)
        client.start()
        
    elif mode == 'c':
        host = input("Enter host IP address: ")
        port = int(input("Enter host port: "))
        client = TriggeredClient(host, port, name, thumper)
        client.start()
