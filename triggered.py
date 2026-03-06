import pygame
import queue

# --- EGA Palette (16 Colors) ---
EGA = {
    'BLACK': (0, 0, 0),
    'BLUE': (0, 0, 170),
    'GREEN': (0, 170, 0),
    'CYAN': (0, 170, 170),
    'RED': (170, 0, 0),
    'MAGENTA': (170, 0, 170),
    'BROWN': (170, 85, 0),
    'LIGHT_GRAY': (170, 170, 170),
    'DARK_GRAY': (85, 85, 85),
    'LIGHT_BLUE': (85, 85, 255),
    'LIGHT_GREEN': (85, 255, 85),
    'LIGHT_CYAN': (85, 255, 255),
    'LIGHT_RED': (255, 85, 85),
    'LIGHT_MAGENTA': (255, 85, 255),
    'YELLOW': (255, 255, 85),
    'WHITE': (255, 255, 255)
}

import socket
import threading
import json
import time
import random
import sys
import os
import pygame
import queue

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

# (Your TriggeredServer class should start right here...)

# --- Network Client (Graphical) ---
class PygameTriggeredClient:
    def __init__(self, host, port, name, thumper):
        self.host = host
        self.port = port
        self.name = name
        self.thumper = thumper
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.msg_queue = queue.Queue()
        self.running = True
        
        # Pygame setup
        pygame.init()
        self.scale = 2
        self.res = (320 * self.scale, 200 * self.scale)
        self.screen = pygame.display.set_mode(self.res)
        pygame.display.set_caption("TRIGGERED - EGA Edition")
        
        # We use a monospace font to simulate DOS/Terminal text
        self.font = pygame.font.SysFont('courier', 12 * self.scale, bold=True)
        self.log = ["Welcome to the Saloon!", "Press 'S' to Start game (if Host)", "Press 'T' to pull the TRIGGER!"]

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            info = json.dumps({'name': self.name, 'thumper': self.thumper})
            self.client_socket.sendall(info.encode())
            self.msg_queue.put("Connected to the server!")
        except ConnectionRefusedError:
            print("Couldn't find the saloon. Make sure the Host has started the server.")
            sys.exit()
            
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        buffer = ""
        while self.running:
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
                            # Split multi-line server messages
                            for m_line in msg['msg'].split('\n'):
                                if m_line:
                                    self.msg_queue.put(m_line)
                        if msg.get('action') == 'quit':
                            self.running = False
                    except Exception:
                        pass
            except:
                self.msg_queue.put("Disconnected from the server.")
                self.running = False
                break

    def draw_text(self):
        self.screen.fill(EGA['BLACK'])
        
        # Draw top banner
        banner = self.font.render(f"GUNSLINGER: {self.name} | THUMPER: {self.thumper}", True, EGA['YELLOW'])
        self.screen.blit(banner, (10, 10))
        pygame.draw.line(self.screen, EGA['BROWN'], (10, 35), (self.res[0]-10, 35), 2)
        
        # Process new messages
        while not self.msg_queue.empty():
            self.log.append(self.msg_queue.get())
            if len(self.log) > 15: # Keep log trimmed to screen height
                self.log.pop(0)
                
        # Draw game log
        y = 50
        for line in self.log:
            # Highlight specific triggers or cards
            color = EGA['LIGHT_GRAY']
            if '>>>' in line: color = EGA['LIGHT_CYAN']
            elif 'BANG' in line or 'Misfire' in line: color = EGA['LIGHT_RED']
            elif 'wins' in line.lower(): color = EGA['LIGHT_GREEN']
                
            text_surface = self.font.render(line, True, color)
            self.screen.blit(text_surface, (10, y))
            y += 20 * (self.scale // 2)

        pygame.display.flip()

    def start(self):
        self.connect()
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t: # QUICK DRAW!
                        self.msg_queue.put(">>> You reached for your iron! <<<")
                        msg = json.dumps({'action': 'trigger'}) + "\n"
                        self.client_socket.sendall(msg.encode())
                    elif event.key == pygame.K_s: # START GAME
                        msg = json.dumps({'action': 'start'}) + "\n"
                        self.client_socket.sendall(msg.encode())
                    elif event.key == pygame.K_r: # RESTART GAME
                        msg = json.dumps({'action': 'restart'}) + "\n"
                        self.client_socket.sendall(msg.encode())

            self.draw_text()
            clock.tick(30) # 30 FPS is plenty for an EGA feel
            
        pygame.quit()
        os._exit(0)

# --- Main Entry Point ---
if __name__ == "__main__":
    print("Welcome to TRIGGERED, partner! (Terminal Setup)")
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
        ai_count = 0
        while True:
            try:
                ai_count = int(input("How many AI players? (0-7): "))
                if 0 <= ai_count <= 7: break
            except ValueError:
                pass
                
        port = int(input("Port to host on (e.g., 5555): "))
        server = TriggeredServer(port, ai_count)
        server.start()
        
        client = PygameTriggeredClient('127.0.0.1', port, name, thumper)
        client.start() # This now opens the Pygame window
        
    elif mode == 'c':
        host = input("Enter host IP address: ")
        port = int(input("Enter host port: "))
        client = PygameTriggeredClient(host, port, name, thumper)
        client.start() # This now opens the Pygame window
