import socket
import threading
import json
import time
import random
import sys
import select

# --- Game Constants and Logic ---
SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
TRIGGER_WINDOW = 3.5  # Seconds allowed to shout "trigger"

def create_deck():
    return [{'suit': s, 'value': v, 'rank': r} for s in SUITS for v, r in VALUES.items()]

def calculate_thumper(age, height, weight):
    return age + height + weight

# --- Network Server ---
class TriggeredServer:
    def __init__(self, port, ai_count):
        self.port = port
        self.ai_count = ai_count
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # conn -> player_info
        self.players = []  # List of player dicts
        self.lock = threading.Lock()
        self.trigger_calls = [] # Store triggers during the window
        
    def start(self):
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(8)
        print(f"Server started on port {self.port}. Waiting for players...")
        
        # Accept clients
        threading.Thread(target=self.accept_clients, daemon=True).start()
        
        input("Press ENTER to start the game when all human players have joined...\n")
        self.start_game()

    def accept_clients(self):
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

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
                print(f"Player {player_info['name']} joined! Thumper Power: {player_info['thumper']}")
                
            while True:
                msg = conn.recv(1024).decode()
                if not msg: break
                parsed = json.loads(msg)
                if parsed.get('action') == 'trigger':
                    with self.lock:
                        self.trigger_calls.append((time.time(), player_info['name']))
        except:
            pass
        finally:
            conn.close()

    def broadcast(self, message):
        msg_str = json.dumps(message)
        with self.lock:
            for conn in list(self.clients.keys()):
                try:
                    conn.sendall(msg_str.encode())
                    time.sleep(0.05) # Prevent message merging
                except:
                    del self.clients[conn]

    def start_game(self):
        # Add AI players
        for i in range(self.ai_count):
            ai_player = {
                'name': f"AI_Bot_{i+1}",
                'thumper': random.randint(100, 300),
                'is_ai': True,
                'score': 0
            }
            self.players.append(ai_player)
            print(f"Added {ai_player['name']}")

        if len(self.players) < 2:
            print("Need at least 2 players to start.")
            sys.exit()

        print("\nDetermining First Dealer based on Thumper Power...")
        # Handle Thumper Power & Ties
        max_thumper = max(p['thumper'] for p in self.players)
        tied_players = [p for p in self.players if p['thumper'] == max_thumper]
        
        if len(tied_players) > 1:
            print("Tie detected! Simulating Rock-Paper-Scissors...")
            time.sleep(1)
            first_dealer = random.choice(tied_players) # Simulating RPS for brevity
            print(f"{first_dealer['name']} won the RPS tie-breaker!")
        else:
            first_dealer = tied_players[0]
            
        print(f"First Dealer is {first_dealer['name']}!")
        
        self.game_loop(first_dealer)

    def game_loop(self, first_dealer):
        deck = create_deck()
        random.shuffle(deck)
        
        dealer_idx = self.players.index(first_dealer)
        original_dealer = first_dealer['name']
        
        while len(deck) >= len(self.players) + 1:
            self.trigger_calls.clear()
            dealer = self.players[dealer_idx]
            self.broadcast({'msg': f"\n--- NEW ROUND --- Dealer: {dealer['name']}"})
            time.sleep(1)
            
            # Deal cards
            round_cards = {}
            for p in self.players:
                round_cards[p['name']] = deck.pop()
            bullseye = deck.pop()
            
            self.broadcast({'msg': f"Cards dealt face down. Bullseye is: {bullseye['value']} of {bullseye['suit']}"})
            time.sleep(2)
            self.broadcast({'msg': f"{dealer['name']} shouts: 'CLICK CLICK'! (Turn over cards!)"})
            
            # Show cards
            cards_display = "Cards revealed: " + ", ".join([f"{name}: {c['value']} of {c['suit']}" for name, c in round_cards.items()])
            self.broadcast({'msg': cards_display})
            self.broadcast({'msg': ">> TYPE 't' AND HIT ENTER IF YOU SEE A MATCH! (3 seconds) <<", 'trigger_phase': True})
            
            # AI Logic - check for match and trigger
            match_exists = any(c['value'] == bullseye['value'] for c in round_cards.values())
            if match_exists:
                for p in self.players:
                    if p['is_ai']:
                        reaction = random.uniform(0.5, 2.8)
                        threading.Timer(reaction, lambda name=p['name']: self.trigger_calls.append((time.time() + reaction, name))).start()

            time.sleep(TRIGGER_WINDOW)
            
            # Evaluate Round
            pot = len(self.players) + 1
            winner = None
            
            with self.lock:
                if self.trigger_calls:
                    self.trigger_calls.sort(key=lambda x: x[0])
                    fastest_time = self.trigger_calls[0][0]
                    # Check for ties in trigger calls (within 0.1 seconds)
                    ties = [name for t, name in self.trigger_calls if t - fastest_time < 0.1]
                    
                    if match_exists:
                        if len(ties) > 1:
                            self.broadcast({'msg': f"Trigger TIE between {', '.join(ties)}! Dealer {dealer['name']} wins by default."})
                            winner = dealer
                        else:
                            winner_name = ties[0]
                            self.broadcast({'msg': f"*** {winner_name} TRIGGERED FIRST! ***"})
                            winner = next(p for p in self.players if p['name'] == winner_name)
                    else:
                        self.broadcast({'msg': f"False trigger! No match existed. Dealer {dealer['name']} wins."})
                        winner = dealer
                else:
                    self.broadcast({'msg': "No triggers called. Evaluating high cards..."})
                    # High card logic
                    max_rank = max(c['rank'] for c in round_cards.values())
                    high_players = [name for name, c in round_cards.items() if c['rank'] == max_rank]
                    
                    if len(high_players) > 1:
                        self.broadcast({'msg': f"Tie for high card! Dealer {dealer['name']} wins."})
                        winner = dealer
                    else:
                        winner_name = high_players[0]
                        self.broadcast({'msg': f"{winner_name} has the high card!"})
                        winner = next(p for p in self.players if p['name'] == winner_name)

            winner['score'] += pot
            self.broadcast({'msg': f"{winner['name']} wins the round and collects {pot} cards!\n"})
            
            # Rotate dealer (Left hand side -> Next index in list)
            dealer_idx = (dealer_idx + 1) % len(self.players)
            time.sleep(2)

        # Game Over
        self.broadcast({'msg': "\n=== GAME OVER! Not enough cards left. ==="})
        remaining = len(deck)
        first_dealer_obj = next(p for p in self.players if p['name'] == original_dealer)
        first_dealer_obj['score'] += remaining
        self.broadcast({'msg': f"First dealer {original_dealer} gets the remaining {remaining} cards."})
        
        # Standings
        self.players.sort(key=lambda x: x['score'], reverse=True)
        standings = "\nFINAL SCORES:\n" + "\n".join([f"{p['name']}: {p['score']} cards" for p in self.players])
        self.broadcast({'msg': standings})
        sys.exit()

# --- Network Client ---
class TriggeredClient:
    def __init__(self, host, port, name, thumper):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.name = name
        self.thumper = thumper

    def start(self):
        self.client_socket.connect((self.host, self.port))
        info = json.dumps({'name': self.name, 'thumper': self.thumper})
        self.client_socket.sendall(info.encode())
        
        threading.Thread(target=self.receive_messages, daemon=True).start()
        
        while True:
            cmd = input()
            if cmd.lower() == 't':
                msg = json.dumps({'action': 'trigger'})
                self.client_socket.sendall(msg.encode())

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(2048).decode()
                if not data: break
                
                # Sockets can merge packets, split by JSON bracket heuristics or use simple try-except
                # For console simplicity, we process raw JSON objects
                try:
                    msg = json.loads(data)
                    if 'msg' in msg:
                        print(msg['msg'])
                except json.JSONDecodeError:
                    # Quick hack to handle merged packets in basic socket dev
                    parts = data.replace('}{', '}split{').split('split')
                    for p in parts:
                        try:
                            msg = json.loads(p)
                            if 'msg' in msg: print(msg['msg'])
                        except: pass
            except:
                print("Disconnected from server.")
                break

# --- Main Entry Point ---
if __name__ == "__main__":
    print("Welcome to TRIGGERED!")
    mode = input("Start as (S)erver/Host or (C)lient? ").strip().lower()
    
    name = input("Enter your name: ")
    age = float(input("Enter your age: "))
    height = float(input("Enter your height (feet): "))
    weight = float(input("Enter your weight (kg): "))
    thumper = calculate_thumper(age, height, weight)
    print(f"Your Thumper Power is: {thumper}\n")

    if mode == 's':
        ai_count = int(input("How many AI players? (1-7): "))
        port = int(input("Port to host on (e.g., 5555): "))
        
        # Start server in background
        server = TriggeredServer(port, ai_count)
        threading.Thread(target=server.start, daemon=True).start()
        
        # Give server time to bind
        time.sleep(1) 
        
        # Connect host as a client to their own server
        client = TriggeredClient('127.0.0.1', port, name, thumper)
        client.start()
        
    elif mode == 'c':
        host = input("Enter host IP address: ")
        port = int(input("Enter host port: "))
        client = TriggeredClient(host, port, name, thumper)
        client.start()
