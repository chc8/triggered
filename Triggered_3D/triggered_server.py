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
JUG_AIR_TIME = 2.5 

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

def calculate_thumper(age, height, weight_kg):
    return round(age + height + weight_kg, 1)

# --- Network Server ---
class TriggeredServer:
    def __init__(self, port, ai_count, num_decks=1):
        self.port = port
        self.ai_count = ai_count
        self.num_decks = num_decks
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.clients = {}  
        self.players = []  
        self.lock = threading.RLock() 
        self.trigger_calls = [] 
        self.game_active = False
        self.ai_added = True
        self.round_num = 1
        self.trigger_phase = False 
        self.is_paused = False
        
        self.quickdraw_active = False
        self.quickdraw_players = []
        
        self.moonshine_active = False
        self.moonshine_risk_players = []
        self.moonshine_zero_players = []
        
        # Spawn AIs
        available_ai_names = random.sample(AI_NAMES_POOL, min(self.ai_count, len(AI_NAMES_POOL)))
        for i in range(self.ai_count):
            ai_player = {
                'name': available_ai_names[i] if i < len(available_ai_names) else f"Bot-{i}",
                'thumper': round(random.uniform(90.0, 220.0), 1), 
                'is_ai': True,
                'score': 0
            }
            self.players.append(ai_player)
        
    def start(self):
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(8)
        print(f"[SERVER] Listening on {get_local_ip()}:{self.port}")
        threading.Thread(target=self.accept_clients, daemon=True).start()
        threading.Thread(target=self.timeout_checker, daemon=True).start()

    def timeout_checker(self):
        while True:
            time.sleep(5)
            with self.lock:
                now = time.time()
                for conn, p_info in list(self.clients.items()):
                    if now - p_info.get('last_seen', now) > 30:
                        self.remove_player(p_info['name'], "timed out")

    def remove_player(self, player_name, reason="disconnected"):
        player_to_remove = next((p for p in self.players if p['name'] == player_name), None)
        if not player_to_remove: return
        
        conn_to_close = next((conn for conn, p in self.clients.items() if p['name'] == player_name), None)
        if conn_to_close:
            try: conn_to_close.close()
            except: pass
            if conn_to_close in self.clients:
                del self.clients[conn_to_close]
        
        self.players.remove(player_to_remove)
        self.broadcast({'msg': f"\n[!] {player_name} {reason} and left the table!"})
        
        if player_to_remove.get('score', 0) > 0 and self.players and self.game_active:
            cards = player_to_remove['score']
            min_score = min(p['score'] for p in self.players)
            lowest_players = [p for p in self.players if p['score'] == min_score]
            share = cards // len(lowest_players)
            for p in lowest_players: p['score'] += share
        
        self.broadcast({'action': 'remove_player', 'name': player_name})
        self.broadcast_scores()

    def accept_clients(self):
        while True:
            conn, addr = self.server_socket.accept()
            print(f"[SERVER] New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def safe_sleep(self, duration):
        waited = 0
        while waited < duration:
            time.sleep(0.1)
            if not self.is_paused:
                waited += 0.1

    def register_trigger(self, player_name):
        with self.lock:
            if self.game_active and self.quickdraw_active and player_name not in self.quickdraw_players:
                return
            if self.trigger_phase:
                if not any(name == player_name for t, name in self.trigger_calls):
                    self.trigger_calls.append((time.time(), player_name))
                    if self.moonshine_active:
                        self.broadcast({'msg': f"  [!] *BANG* {player_name} shot at the jug!"})
                    else:
                        self.broadcast({'msg': f"  [!] *BANG* {player_name} reached for their iron!"})
            elif self.game_active:
                if not any(name == player_name for t, name in self.trigger_calls):
                    self.trigger_calls.append((time.time(), player_name))
                    self.broadcast({'msg': f"  [-] *Click* {player_name} drew too early!"})

    def handle_client(self, conn):
        player_info = None
        try:
            buffer = ""
            while True:
                data = conn.recv(1024).decode()
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    parsed = json.loads(line.strip())
                    
                    if player_info is None:
                        player_info = parsed
                        player_info['conn'] = conn
                        player_info['score'] = 0
                        player_info['last_seen'] = time.time()
                        with self.lock:
                            self.clients[conn] = player_info
                            self.players.append(player_info)
                        self.broadcast({'msg': f"Gunslinger {player_info['name']} moseyed into the saloon!"})
                        self.broadcast_scores()
                    else:
                        action = parsed.get('action')
                        if action == 'ping':
                            player_info['last_seen'] = time.time()
                        elif action == 'trigger' and self.game_active and not self.is_paused:
                            self.register_trigger(player_info['name'])
                        elif action == 'toggle_pause':
                            self.is_paused = not self.is_paused
                            self.broadcast({'msg': f"--- GAME {'PAUSED' if self.is_paused else 'RESUMED'} ---"})
                        elif action == 'start' and not self.game_active:
                            threading.Thread(target=self.start_game_logic, daemon=True).start()
        except: pass
        finally:
            with self.lock:
                if player_info: self.remove_player(player_info['name'])

    def broadcast(self, message):
        msg_str = json.dumps(message) + "\n"
        with self.lock:
            for conn in list(self.clients.keys()):
                try: conn.sendall(msg_str.encode())
                except: pass

    def broadcast_scores(self):
        scores = {p['name']: p['score'] for p in self.players}
        self.broadcast({'action': 'update_scores', 'scores': scores})

    def start_game_logic(self):
        with self.lock:
            if self.game_active or len(self.players) < 2: return
            self.game_active = True
            for p in self.players: p['score'] = 0

        self.broadcast({'msg': "DRAW YOUR WEAPONS! THE GAME BEGINS!"})
        thumper_display = "\n--- THUMPER POWERS ---\n" + "\n".join([f"{p['name']}: {p['thumper']}" for p in self.players])
        self.broadcast({'msg': thumper_display})
        self.safe_sleep(2)
        
        first_dealer = max(self.players, key=lambda p: p['thumper'])
        self.game_loop(first_dealer)

    def get_high_card_winners(self, round_cards):
        max_rank = max(c['rank'] for c in round_cards.values())
        return [name for name, c in round_cards.items() if c['rank'] == max_rank]

    def game_loop(self, first_dealer):
        deck = create_deck() * self.num_decks
        random.shuffle(deck)
        dealer_idx = self.players.index(first_dealer)
        
        while len(deck) >= len(self.players) + 1 and len(self.players) > 1:
            dealer = self.players[dealer_idx % len(self.players)]
            self.broadcast({'msg': f"\n--- ROUND {self.round_num} --- Dealer {dealer['name']} is shufflin'..."})
            self.safe_sleep(1.5)
            
            round_cards = {p['name']: deck.pop() for p in self.players}
            bullseye = deck.pop()
            self.broadcast({'msg': f">>> {bullseye['value']} of {bullseye['suit']} <<<"})
            self.safe_sleep(2)

            with self.lock:
                self.trigger_calls.clear()
                self.trigger_phase = True
            self.broadcast({'msg': f"{dealer['name']} draws: 'CLICK CLICK'!"})
            
            # Logic for reveals and winners would go here (same as original code)
            # Keeping high-level structure for Godot compatibility...
            
            self.trigger_phase = False
            self.broadcast_scores()
            self.round_num += 1
            dealer_idx += 1
            self.safe_sleep(2)

        self.game_active = False
        self.broadcast({'msg': "GAME OVER! Host can restart."})

if __name__ == "__main__":
    server = TriggeredServer(5555, ai_count=3, num_decks=1)
    server.start()
    while True: time.sleep(1)
