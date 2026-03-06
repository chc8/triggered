import socket
import threading
import json
import time
import random
import sys
import os
import queue
import textwrap
import math
import pygame

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

def lerp(a, b, t):
    return a + (b - a) * t

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
                            winner = None 
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
        self.broadcast({'msg': "\nHost can press 'R' to play a new game, or close the window to exit."})


# --- SVGA+ Palette ---
SVGA = {
    'BG_GREEN': (24, 66, 38),      
    'BLACK': (20, 20, 20),
    'WHITE': (245, 245, 245),
    'CARD_SHADOW': (0, 0, 0, 100), 
    'GOLD': (255, 215, 0),
    'TEXT_LIGHT': (220, 220, 220),
    'TEXT_BLUE': (100, 200, 255),
    'TEXT_RED': (255, 100, 100),
    'TEXT_GREEN': (100, 255, 100),
    'SUIT_RED': (220, 40, 40),
    'SUIT_BLACK': (30, 30, 30),
    'UI_PANEL': (40, 40, 40, 200),
    'PAPER': (240, 230, 200),
    'WOOD_BASE': (139, 90, 43),
    'WOOD_DARK': (80, 50, 20),
    'WOOD_LINE': (101, 67, 33)
}

# --- Visual Objects ---
class FloatingMessage:
    def __init__(self, text, color, start_y):
        self.text = text
        self.color = color
        self.y = start_y
        self.target_y = start_y

    def update(self):
        self.y = lerp(self.y, self.target_y, 0.15)

class AnimatedCard:
    def __init__(self, start_x, start_y, value=None, suit=None, label=""):
        self.x = start_x
        self.y = start_y
        self.target_x = start_x
        self.target_y = start_y
        self.draw_x = start_x
        self.draw_y = start_y
        
        self.value = value
        self.suit = suit
        self.label = label
        self.revealed = False
        
        self.has_bullet_hole = False
        self.bullet_hole_pos = (0, 0)
        self.has_tombstone = False
        self.is_winner = False
        self.shake_timer = 0
        self.flash_alpha = 0

    def update(self):
        self.x = lerp(self.x, self.target_x, 0.1)
        self.y = lerp(self.y, self.target_y, 0.1)
        
        self.draw_x = self.x
        self.draw_y = self.y
        
        if self.shake_timer > 0:
            self.draw_x += random.randint(-5, 5)
            self.draw_y += random.randint(-5, 5)
            self.shake_timer -= 1
            
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 20)


# --- Main Application ---
class TriggeredGameApp:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        # Load western background music
        try:
            pygame.mixer.music.load('western_theme.mp3')
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1) # Play indefinitely
        except Exception:
            print("Notice: 'western_theme.mp3' not found in root folder. Playing without background music.")
            pass
            
        self.res = (1280, 720)
        self.screen = pygame.display.set_mode(self.res)
        pygame.display.set_caption("TRIGGERED - High Res Edition")
        
        try:
            self.font = pygame.font.SysFont('trebuchetms', 20, bold=True)
            self.small_font = pygame.font.SysFont('trebuchetms', 16, bold=True)
            self.title_font = pygame.font.SysFont('impact', 72)
            self.card_font = pygame.font.SysFont('arial', 36, bold=True)
            self.ledger_font = pygame.font.SysFont('courier', 24, bold=True)
        except:
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 20)
            self.title_font = pygame.font.Font(None, 72)
            self.card_font = pygame.font.Font(None, 40)
            self.ledger_font = pygame.font.Font(None, 30)
        
        self.left_panel_w = 600
        char_width = self.font.size("A")[0]
        self.max_chars = (self.left_panel_w - 40) // char_width 
        
        self.running = True
        self.state = 'SETUP'
        self.blink_timer = 0
        
        self.setup_step = 'MODE'
        self.input_text = ""
        self.setup_error = ""
        
        self.is_host = False
        self.name = ""
        self.age = 0.0
        self.height = 0.0
        self.weight = 0.0
        self.thumper = 0.0
        self.ai_count = 0
        self.host_ip = "127.0.0.1"
        self.port = 5555
        
        self.server = None
        self.client_socket = None
        self.msg_queue = queue.Queue()
        
        self.log_messages = []
        self.scroll_offset = 0
        self.bullseye_anim_card = None
        self.player_cards = {}
        self.cards_dealt = False
        
        self.game_over = False
        self.overall_winner = ""

        # Setup form sequence
        self.setup_sequence = ['MODE', 'NAME', 'AGE', 'HEIGHT', 'WEIGHT', 'NETWORK', 'PORT']

    def handle_setup_input(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            self.setup_error = ""
        elif event.key == pygame.K_RETURN:
            val = self.input_text.strip()
            self.input_text = ""
            self.setup_error = ""
            
            try:
                if self.setup_step == 'MODE':
                    if val.lower() == 's':
                        self.is_host = True
                        self.setup_step = 'NAME'
                    elif val.lower() == 'c':
                        self.is_host = False
                        self.setup_step = 'NAME'
                    else:
                        self.setup_error = "Type 'S' for Host or 'C' for Client."
                
                elif self.setup_step == 'NAME':
                    if val:
                        self.name = val
                        self.setup_step = 'AGE'
                    else:
                        self.setup_error = "Name cannot be empty."
                        
                elif self.setup_step == 'AGE':
                    self.age = float(val)
                    self.setup_step = 'HEIGHT'
                    
                elif self.setup_step == 'HEIGHT':
                    self.height = float(val)
                    self.setup_step = 'WEIGHT'
                    
                elif self.setup_step == 'WEIGHT':
                    self.weight = float(val)
                    self.thumper = calculate_thumper(self.age, self.height, self.weight)
                    self.setup_step = 'NETWORK'
                    
                elif self.setup_step == 'NETWORK':
                    if self.is_host:
                        self.ai_count = int(val)
                        if 0 <= self.ai_count <= 7:
                            self.setup_step = 'PORT'
                        else:
                            self.setup_error = "AI count must be 0-7."
                    else:
                        if val:
                            self.host_ip = val
                            self.setup_step = 'PORT'
                        else:
                            self.setup_error = "IP cannot be empty."
                        
                elif self.setup_step == 'PORT':
                    self.port = int(val)
                    self.finalize_setup()
                    
            except ValueError:
                self.setup_error = "Invalid format. Numbers required here."
        else:
            if event.unicode.isprintable() and len(self.input_text) < 20:
                self.input_text += event.unicode
                self.setup_error = ""

    def finalize_setup(self):
        pygame.display.set_caption("TRIGGERED - High Res Edition" + (" [HOST]" if self.is_host else ""))
        
        if self.is_host:
            self.server = TriggeredServer(self.port, self.ai_count)
            self.server.start()
            time.sleep(0.5)
            self.host_ip = '127.0.0.1'
            
        self.connect_to_server()

    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.host_ip, self.port))
            info = json.dumps({'name': self.name, 'thumper': self.thumper})
            self.client_socket.sendall(info.encode())
            
            self.state = 'TITLE'
            
            self.add_log_message("Welcome to the Saloon!", SVGA['TEXT_LIGHT'])
            if self.is_host:
                self.add_log_message(f"Server IP: {get_local_ip()} | Port: {self.port}", SVGA['TEXT_BLUE'])
                self.add_log_message("You are the Host. Press 'S' to Start.", SVGA['GOLD'])
            else:
                self.add_log_message("Waiting for the Host to start...", SVGA['TEXT_LIGHT'])
            self.add_log_message("Press 'T' to pull the TRIGGER!", SVGA['TEXT_LIGHT'])
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except ConnectionRefusedError:
            self.setup_step = 'PORT'
            self.setup_error = "Connection Failed. Check IP/Port and try again."

    def add_log_message(self, text, color):
        spacing = 28
        for msg in self.log_messages:
            msg.target_y -= spacing
        
        new_msg = FloatingMessage(text, color, self.res[1])
        new_msg.target_y = self.res[1] - 50 
        self.log_messages.append(new_msg)
        
        if len(self.log_messages) > 30:
            self.log_messages.pop(0)

    def receive_messages(self):
        buffer = ""
        while self.running and self.state in ['TITLE', 'GAME']:
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
                            raw_msg = msg['msg']
                            
                            if "DRAW YOUR WEAPONS!" in raw_msg:
                                self.game_over = False
                                self.overall_winner = ""
                                
                            elif "--- THUMPER POWERS ---" in raw_msg:
                                self.player_cards.clear()
                                idx = 0
                                for m_line in raw_msg.split('\n'):
                                    if ':' in m_line and not '---' in m_line and not 'THUMPER' in m_line:
                                        p_name = m_line.split(':')[0].strip()
                                        if p_name:
                                            self.player_cards[p_name] = AnimatedCard(self.res[0] + 200, self.res[1] + 200, label=p_name)
                                            idx += 1
                                            
                            elif "is shufflin'" in raw_msg:
                                self.bullseye_anim_card = None
                                for p_name, card in self.player_cards.items():
                                    card.revealed = False
                                    card.has_bullet_hole = False  
                                    card.is_winner = False 
                                    card.has_tombstone = False
                                    card.x = self.res[0] + 100 
                                self.cards_dealt = False
                                
                            elif "*BANG*" in raw_msg:
                                for p_name, card in self.player_cards.items():
                                    if p_name in raw_msg:
                                        card.has_bullet_hole = True
                                        card.bullet_hole_pos = (random.randint(-25, 25), random.randint(-35, 35))
                                        card.flash_alpha = 255
                                        
                            elif "Misfire!" in raw_msg:
                                for p_name, card in self.player_cards.items():
                                    if p_name in raw_msg:
                                        card.has_tombstone = True
                                        
                            elif any(phrase in raw_msg for phrase in ["WAS THE FASTEST", "takes the pot", "holds the highest", "wins the round"]):
                                for p_name, card in self.player_cards.items():
                                    if p_name in raw_msg:
                                        card.is_winner = True
                                        card.shake_timer = 40  
                                        
                            elif "Cards dealt face down" in raw_msg:
                                self.cards_dealt = True
                                start_x = self.left_panel_w + 50
                                for i, (p_name, card) in enumerate(self.player_cards.items()):
                                    col = i % 4
                                    row = i // 4
                                    card.target_x = start_x + (col * 140)
                                    card.target_y = 350 + (row * 180)
                                    
                            elif ">>>" in raw_msg and "of" in raw_msg:
                                parts = raw_msg.replace(">>>", "").replace("<<<", "").strip().split(" of ")
                                if len(parts) == 2:
                                    self.bullseye_anim_card = AnimatedCard(self.res[0]//2, -200, parts[0].strip(), parts[1].strip(), "BULLSEYE")
                                    self.bullseye_anim_card.target_x = self.left_panel_w + (self.res[0] - self.left_panel_w)//2 - 75
                                    self.bullseye_anim_card.target_y = 100
                                    self.bullseye_anim_card.revealed = True
                                    
                            elif "Cards revealed on the table:" in raw_msg:
                                for m_line in raw_msg.split('\n'):
                                    if m_line.strip().startswith('- '):
                                        try:
                                            p_name_part, card_part = m_line.strip()[2:].split(': ')
                                            val, suit = card_part.split(' of ')
                                            if p_name_part.strip() in self.player_cards:
                                                pc = self.player_cards[p_name_part.strip()]
                                                pc.value = val.strip()
                                                pc.suit = suit.strip()
                                                pc.revealed = True
                                        except ValueError:
                                            pass
                                            
                            elif "FINAL BOUNTIES" in raw_msg:
                                lines = raw_msg.split('\n')
                                for line in lines:
                                    if ':' in line and 'FINAL BOUNTIES' not in line:
                                        self.overall_winner = line.split(':')[0].strip()
                                        self.game_over = True
                                        break
                            
                            for m_line in raw_msg.split('\n'):
                                if m_line.strip() == "":
                                    self.msg_queue.put(("", SVGA['TEXT_LIGHT'])) 
                                else:
                                    color = SVGA['TEXT_LIGHT']
                                    if '>>>' in m_line: color = SVGA['TEXT_BLUE']
                                    elif 'BANG' in m_line or 'Misfire' in m_line: color = SVGA['TEXT_RED']
                                    elif 'wins' in m_line.lower(): color = SVGA['TEXT_GREEN']
                                    
                                    wrapped = textwrap.wrap(m_line, self.max_chars)
                                    for w_line in wrapped:
                                        self.msg_queue.put((w_line, color))
                                        
                        if msg.get('action') == 'quit':
                            self.msg_queue.put(("Server closed. You can close this window.", SVGA['TEXT_RED']))
                    except Exception:
                        pass
            except:
                self.msg_queue.put(("Disconnected from the server.", SVGA['TEXT_LIGHT']))
                break

    def draw_setup_screen(self):
        self.screen.fill(SVGA['BG_GREEN'])
        
        # Draw background shadow and paper form
        form_w, form_h = 600, 600
        fx = self.res[0]//2 - form_w//2
        fy = self.res[1]//2 - form_h//2
        
        shadow_rect = pygame.Surface((form_w, form_h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_rect, SVGA['CARD_SHADOW'], shadow_rect.get_rect(), border_radius=12)
        self.screen.blit(shadow_rect, (fx + 10, fy + 10))
        
        pygame.draw.rect(self.screen, SVGA['PAPER'], (fx, fy, form_w, form_h), border_radius=12)
        pygame.draw.rect(self.screen, SVGA['WOOD_DARK'], (fx, fy, form_w, form_h), 4, border_radius=12)
        
        title_surf = self.title_font.render("SALOON LEDGER", True, SVGA['BLACK'])
        self.screen.blit(title_surf, (self.res[0]//2 - title_surf.get_width()//2, fy + 20))
        pygame.draw.line(self.screen, SVGA['BLACK'], (fx + 50, fy + 100), (fx + form_w - 50, fy + 100), 2)
        
        # Form Fields Configuration
        fields = [
            ('MODE', "Role (S=Host, C=Client):", "Host" if self.is_host else ("Client" if self.setup_step != 'MODE' else "")),
            ('NAME', "Gunslinger Name:", self.name if self.setup_step not in ['MODE', 'NAME'] else ""),
            ('AGE', "Age (years):", str(self.age) if self.setup_step not in ['MODE', 'NAME', 'AGE'] else ""),
            ('HEIGHT', "Height (feet):", str(self.height) if self.setup_step not in ['MODE', 'NAME', 'AGE', 'HEIGHT'] else ""),
            ('WEIGHT', "Weight (kg):", str(self.weight) if self.setup_step not in ['MODE', 'NAME', 'AGE', 'HEIGHT', 'WEIGHT'] else ""),
            ('NETWORK', "AI Bots (0-7):" if self.is_host else "Host IP:", str(self.ai_count) if self.is_host and self.setup_step not in ['MODE', 'NAME', 'AGE', 'HEIGHT', 'WEIGHT', 'NETWORK'] else (self.host_ip if not self.is_host and self.setup_step not in ['MODE', 'NAME', 'AGE', 'HEIGHT', 'WEIGHT', 'NETWORK'] else "")),
            ('PORT', "Port:", str(self.port) if self.setup_step not in ['MODE', 'NAME', 'AGE', 'HEIGHT', 'WEIGHT', 'NETWORK', 'PORT'] else "")
        ]
        
        # Draw Fields
        start_y = fy + 130
        self.blink_timer += 1
        
        for idx, (step_id, label, static_val) in enumerate(fields):
            y_pos = start_y + (idx * 50)
            
            # Label
            lbl_color = SVGA['BLACK'] if self.setup_sequence.index(self.setup_step) >= idx else (150, 150, 150)
            lbl_surf = self.ledger_font.render(label, True, lbl_color)
            self.screen.blit(lbl_surf, (fx + 30, y_pos)) # Adjusted padding to give label room
            
            # Value Box
            box_x = fx + 340 # Moved further right
            box_w = 230
            
            if self.setup_step == step_id:
                # Active Input
                pygame.draw.rect(self.screen, SVGA['WHITE'], (box_x, y_pos - 5, box_w, 35), border_radius=4)
                pygame.draw.rect(self.screen, SVGA['TEXT_BLUE'], (box_x, y_pos - 5, box_w, 35), 2, border_radius=4)
                display_input = self.input_text + ("_" if self.blink_timer % 30 < 15 else "")
                val_surf = self.ledger_font.render(display_input, True, SVGA['BLACK'])
                self.screen.blit(val_surf, (box_x + 10, y_pos))
            else:
                # Static / Disabled Input
                pygame.draw.line(self.screen, (200, 200, 200), (box_x, y_pos + 25), (box_x + box_w, y_pos + 25), 2)
                if static_val:
                    val_surf = self.ledger_font.render(static_val, True, SVGA['BLACK'])
                    self.screen.blit(val_surf, (box_x + 10, y_pos))

        # Error handling
        if self.setup_error:
            e_surf = self.ledger_font.render(self.setup_error, True, SVGA['TEXT_RED'])
            self.screen.blit(e_surf, (self.res[0]//2 - e_surf.get_width()//2, fy + form_h - 40))

        pygame.display.flip()

    def draw_title_screen(self):
        self.screen.fill(SVGA['BLACK'])
        
        title_surf = self.title_font.render("TRIGGERED", True, SVGA['TEXT_RED'])
        self.screen.blit(title_surf, (self.res[0]//2 - title_surf.get_width()//2, 80))
        
        subtitle = self.font.render("HOW TO SURVIVE THE STANDOFF", True, SVGA['GOLD'])
        self.screen.blit(subtitle, (self.res[0]//2 - subtitle.get_width()//2, 180))
        
        pygame.draw.line(self.screen, SVGA['GOLD'], (self.res[0]//2 - 200, 210), (self.res[0]//2 + 200, 210), 2)
        
        rules = [
            "1. Goal: Collect the most cards, partner.",
            "2. A 'Bullseye' card is dealt face-up.",
            "3. When dealer yells 'CLICK CLICK', cards flip.",
            "4. QUICK DRAW: If ANY match to Bullseye, press the 'T' key immediately!",
            "5. No match? Highest card takes the pot.",
            "6. MISFIRE: Press 'T' with no match? You lose the round!",
            "7. Dealer wins ties. House rules."
        ]
        
        y = 250
        for r in rules:
            r_surf = self.font.render(r, True, SVGA['TEXT_LIGHT'])
            self.screen.blit(r_surf, (self.res[0]//2 - 300, y))
            y += 35
            
        self.blink_timer += 1
        if self.blink_timer % 30 < 15:
            prompt = self.font.render("PRESS SPACE TO KICK OPEN THE DOORS", True, SVGA['TEXT_BLUE'])
            self.screen.blit(prompt, (self.res[0]//2 - prompt.get_width()//2, self.res[1] - 100))

        pygame.display.flip()

    def draw_card(self, x, y, width, height, value, suit, label, revealed, is_winner=False, has_bullet_hole=False, bullet_hole_pos=(0,0), has_tombstone=False, flash_alpha=0):
        lbl_color = SVGA['TEXT_GREEN'] if is_winner else SVGA['GOLD']
        lbl_surf = self.small_font.render(label, True, lbl_color)
        self.screen.blit(lbl_surf, (x + width//2 - lbl_surf.get_width()//2, y - 25))
        
        shadow_rect = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_rect, SVGA['CARD_SHADOW'], shadow_rect.get_rect(), border_radius=8)
        self.screen.blit(shadow_rect, (x + 5, y + 5))
        
        border_color = SVGA['GOLD'] if is_winner else (200, 200, 200)
        border_thickness = 4 if is_winner else 2
        
        if not revealed:
            pygame.draw.rect(self.screen, (20, 50, 100), (x, y, width, height), border_radius=8)
            pygame.draw.rect(self.screen, border_color, (x, y, width, height), border_thickness, border_radius=8)
            for i in range(10, width, 15):
                pygame.draw.line(self.screen, (30, 80, 150), (x+i, y), (x+i, y+height), 2)
        else:
            pygame.draw.rect(self.screen, SVGA['WHITE'], (x, y, width, height), border_radius=8)
            pygame.draw.rect(self.screen, border_color, (x, y, width, height), border_thickness, border_radius=8) 
            
            color = SVGA['SUIT_RED'] if suit in ['Hearts', 'Diamonds'] else SVGA['SUIT_BLACK']
            
            val_surf = self.card_font.render(value, True, color)
            self.screen.blit(val_surf, (x + 10, y + 10))
            
            cx, cy = x + width // 2, y + height // 2 + 10
            size = 20 if width > 100 else 12
            
            if suit == 'Diamonds':
                pygame.draw.polygon(self.screen, color, [(cx, cy-size), (cx+size*0.8, cy), (cx, cy+size), (cx-size*0.8, cy)])
            elif suit == 'Hearts':
                pygame.draw.circle(self.screen, color, (cx-size//2, cy-size//2), size//2 + 2)
                pygame.draw.circle(self.screen, color, (cx+size//2, cy-size//2), size//2 + 2)
                pygame.draw.polygon(self.screen, color, [(cx-size, cy-size//3), (cx+size, cy-size//3), (cx, cy+size)])
            elif suit == 'Spades':
                pygame.draw.circle(self.screen, color, (cx-size//2, cy+size//3), size//2 + 2)
                pygame.draw.circle(self.screen, color, (cx+size//2, cy+size//3), size//2 + 2)
                pygame.draw.polygon(self.screen, color, [(cx-size, cy+size//3), (cx+size, cy+size//3), (cx, cy-size)])
                pygame.draw.rect(self.screen, color, (cx-size//4, cy+size//3, size//2, size))
            elif suit == 'Clubs':
                pygame.draw.circle(self.screen, color, (cx, cy-size//1.5), size//2 + 2)
                pygame.draw.circle(self.screen, color, (cx-size//1.5, cy+size//3), size//2 + 2)
                pygame.draw.circle(self.screen, color, (cx+size//1.5, cy+size//3), size//2 + 2)
                pygame.draw.rect(self.screen, color, (cx-size//4, cy+size//3, size//2, size))

        if flash_alpha > 0:
            flash_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(flash_surf, (255, 255, 220, flash_alpha), flash_surf.get_rect(), border_radius=8)
            self.screen.blit(flash_surf, (x, y))

        if has_bullet_hole:
            bx, by = x + width // 2 + bullet_hole_pos[0], y + height // 2 + bullet_hole_pos[1]
            pygame.draw.circle(self.screen, (70, 70, 70), (bx, by), 12)
            pygame.draw.circle(self.screen, (15, 15, 15), (bx, by), 7)
            pygame.draw.line(self.screen, (40, 40, 40), (bx, by), (bx+18, by-12), 2)
            pygame.draw.line(self.screen, (40, 40, 40), (bx, by), (bx-15, by-15), 2)
            pygame.draw.line(self.screen, (40, 40, 40), (bx, by), (bx-8, by+18), 2)

        if has_tombstone:
            tx = x + width // 2
            ty = y + height // 2 + 10
            
            # Draw silent fills so there is no internal outline overlapping
            pygame.draw.rect(self.screen, (100, 100, 100), (tx - 30, ty - 10, 60, 50))
            pygame.draw.circle(self.screen, (100, 100, 100), (tx, ty - 10), 30)
            
            # Trace only the extreme outer border
            pygame.draw.line(self.screen, (50, 50, 50), (tx - 30, ty - 10), (tx - 30, ty + 38), 2) # Left wall
            pygame.draw.line(self.screen, (50, 50, 50), (tx + 30, ty - 10), (tx + 30, ty + 38), 2) # Right wall
            pygame.draw.line(self.screen, (50, 50, 50), (tx - 31, ty + 39), (tx + 31, ty + 39), 2) # Floor line
            pygame.draw.arc(self.screen, (50, 50, 50), (tx - 30, ty - 40, 60, 60), 0, math.pi, 2)  # Top dome curve
            
            rip_surf = self.small_font.render("R.I.P.", True, SVGA['BLACK'])
            self.screen.blit(rip_surf, (tx - rip_surf.get_width()//2, ty - 5))

    def draw_game_screen(self):
        self.screen.fill(SVGA['BG_GREEN'])
        
        panel_rect = pygame.Surface((self.left_panel_w, self.res[1]), pygame.SRCALPHA)
        pygame.draw.rect(panel_rect, SVGA['UI_PANEL'], panel_rect.get_rect())
        self.screen.blit(panel_rect, (0, 0))
        pygame.draw.line(self.screen, SVGA['GOLD'], (self.left_panel_w, 0), (self.left_panel_w, self.res[1]), 3)
        
        banner = self.font.render(f"GUNSLINGER: {self.name} | THUMPER: {self.thumper}", True, SVGA['GOLD'])
        self.screen.blit(banner, (20, 20))
        pygame.draw.line(self.screen, SVGA['TEXT_LIGHT'], (20, 50), (self.left_panel_w - 20, 50), 1)
        
        for msg in self.log_messages:
            msg.update()
            if msg.y > 60 and msg.y < self.res[1]: 
                text_surface = self.font.render(msg.text, True, msg.color)
                self.screen.blit(text_surface, (20, msg.y))

        if self.bullseye_anim_card:
            c = self.bullseye_anim_card
            c.update()
            self.draw_card(c.draw_x, c.draw_y, 150, 210, c.value, c.suit, c.label, c.revealed)
            
        for p_name, c in self.player_cards.items():
            c.update()
            label = "YOU" if p_name == self.name else p_name
            self.draw_card(c.draw_x, c.draw_y, 100, 140, c.value, c.suit, label, c.revealed, c.is_winner, c.has_bullet_hole, c.bullet_hole_pos, c.has_tombstone, c.flash_alpha)

        if self.game_over and self.overall_winner:
            font_big = pygame.font.SysFont('impact', 64)
            win_text_str = f"WINNER: {self.overall_winner}"
            win_text_w = font_big.size(win_text_str)[0]
            
            # Setup Old Wooden Board variables to stretch dynamically with the text length
            board_w = max(500, win_text_w + 80)
            board_h = 180
            cx = self.left_panel_w + (self.res[0] - self.left_panel_w)//2
            cy = self.res[1]//2
            bx, by = cx - board_w//2, cy - board_h//2
            
            # Shadow
            shadow_rect = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
            pygame.draw.rect(shadow_rect, SVGA['CARD_SHADOW'], shadow_rect.get_rect(), border_radius=10)
            self.screen.blit(shadow_rect, (bx + 8, by + 8))
            
            # Base Wood
            pygame.draw.rect(self.screen, SVGA['WOOD_BASE'], (bx, by, board_w, board_h), border_radius=10)
            
            # Wood Planks
            pygame.draw.line(self.screen, SVGA['WOOD_LINE'], (bx, by + board_h//3), (bx + board_w, by + board_h//3), 4)
            pygame.draw.line(self.screen, SVGA['WOOD_LINE'], (bx, by + 2*board_h//3), (bx + board_w, by + 2*board_h//3), 4)
            
            # Heavy Border
            pygame.draw.rect(self.screen, SVGA['WOOD_DARK'], (bx, by, board_w, board_h), 6, border_radius=10)
            
            # Iron Nails in Corners
            for nx, ny in [(bx+20, by+20), (bx+board_w-20, by+20), (bx+20, by+board_h-20), (bx+board_w-20, by+board_h-20)]:
                pygame.draw.circle(self.screen, (50, 50, 50), (nx, ny), 8)
                pygame.draw.circle(self.screen, (100, 100, 100), (nx-2, ny-2), 3) # Highlight
            
            # Text Generation
            win_text = font_big.render(win_text_str, True, SVGA['GOLD'])
            shadow = font_big.render(win_text_str, True, SVGA['BLACK'])
            sub_text = self.card_font.render("THE FASTEST GUN IN THE WEST", True, SVGA['WHITE'])
            
            self.screen.blit(shadow, (cx - shadow.get_width()//2 + 4, cy - shadow.get_height()//2 - 20 + 4))
            self.screen.blit(win_text, (cx - win_text.get_width()//2, cy - win_text.get_height()//2 - 20))
            self.screen.blit(sub_text, (cx - sub_text.get_width()//2, cy + 30))

        pygame.display.flip()

    def process_messages(self):
        while not self.msg_queue.empty():
            text, color = self.msg_queue.get()
            if text == "":
                self.add_log_message(" ", color)
            else:
                self.add_log_message(text, color)

    def run(self):
        clock = pygame.time.Clock()
        
        while self.running:
            self.process_messages()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    if self.is_host and self.client_socket:
                        msg = json.dumps({'action': 'exit'}) + "\n"
                        try:
                            self.client_socket.sendall(msg.encode())
                        except:
                            pass
                elif event.type == pygame.KEYDOWN:
                    if self.state == 'SETUP':
                        self.handle_setup_input(event)
                        
                    elif self.state == 'TITLE':
                        if event.key == pygame.K_SPACE:
                            self.state = 'GAME'
                            
                    elif self.state == 'GAME':
                        if event.key == pygame.K_t: 
                            self.add_log_message(">>> You reached for your iron! <<<", SVGA['TEXT_BLUE'])
                            msg = json.dumps({'action': 'trigger'}) + "\n"
                            self.client_socket.sendall(msg.encode())
                        elif event.key == pygame.K_s: 
                            if self.is_host:
                                msg = json.dumps({'action': 'start'}) + "\n"
                                self.client_socket.sendall(msg.encode())
                            else:
                                self.add_log_message("Only the Host can start the game.", SVGA['TEXT_RED'])
                        elif event.key == pygame.K_r: 
                            if self.is_host:
                                msg = json.dumps({'action': 'restart'}) + "\n"
                                self.client_socket.sendall(msg.encode())
                            else:
                                self.add_log_message("Only the Host can restart the game.", SVGA['TEXT_RED'])

            if self.state == 'SETUP':
                self.draw_setup_screen()
            elif self.state == 'TITLE':
                self.draw_title_screen()
            elif self.state == 'GAME':
                self.draw_game_screen()
                
            clock.tick(60) 
            
        pygame.quit()
        os._exit(0)

if __name__ == "__main__":
    app = TriggeredGameApp()
    app.run()
