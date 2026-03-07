```markdown
# 🌵 TRIGGERED 

```text
  _______ _____  _____  _____  _____  ______ _____  ______ _____  
 |__   __|  __ \|_   _|/ ____|/ ____||  ____|  __ \|  ____|  __ \ 
    | |  | |__) | | | | |  __| |  __ | |__  | |__) | |__  | |  | |
    | |  |  _  /  | | | | |_ | | |_ ||  __| |  _  /|  __| | |  | |
    | |  | | \ \ _| |_| |__| | |__| || |____| | \ \| |____| |__| |
    |_|  |_|  \_\______\_____|\_____||______|_|  \_\______|_____/ 

      .---.
     /_____\
     |     |
     |     |
     |     |
     |     |
     |     |
     |_____|
     [_____]
     Colt .45

```

**Triggered** is a high-resolution, smooth-scrolling networked multiplayer card game built in Python using Pygame. Set in the tense atmosphere of a Wild West saloon, players test their reflexes against friends and AI bots in a deadly standoff.

If you match the Bullseye, be the first to reach for your iron. But draw too early, and you'll end up with a tombstone.

---

## ✨ Features

* **Networked Multiplayer:** Client/Server architecture over TCP sockets allowing LAN or WAN play.
* **AI Gunslingers:** Fill empty seats at your table with customizable bot opponents.
* **Modern SVGA+ Graphics:** Crisp 720p rendering, TrueType anti-aliased fonts, and a casino-green felt table.
* **Smooth Animations:** 60 FPS Linear Interpolation (Lerp) for buttery-smooth card dealing and UI scrolling.
* **Visceral Visual Effects:** Procedural screen flashes, dynamic screen-shake on round wins, and localized bullet hole mapping (you can even shoot your own card!).
* **Dynamic End-Screen:** A procedurally drawn wooden bounty board dynamically scales to fit the name of the ultimate winner.
* **Audio Support:** Drop in your own Western theme and Colt gunshot sound effects for full immersion.

---

## 🛠️ Requirements

* **Python 3.7+**
* **Pygame** (`pip install pygame`)

---

## 🚀 Installation & Setup

1. **Clone the repository:**
```bash
git clone [https://github.com/yourusername/triggered.git](https://github.com/yourusername/triggered.git)
cd triggered

```


2. **Install dependencies:**
```bash
pip install pygame

```


3. **Add Audio Assets (Optional but recommended):**
Place the following files in the root directory next to the python script:
* `western_theme.mp3` (Plays on loop in the background)
* `gunshot.wav` or `gunshot.mp3` (Plays when a player triggers)


4. **Run the game:**
```bash
python triggered.py

```



---

## 🎮 How to Play

### 1. The Saloon Ledger (Setup)

When launching the game, you will be prompted to fill out the Saloon Ledger:

* **Role:** Choose `S` to host the game (start the server) or `C` to join an existing game as a client.
* **Stats (Age, Height, Weight):** These calculate your **Thumper** power. The player with the highest Thumper stat becomes the First Dealer.
* **Network:** Hosts will set the number of AI bots (0-7). Clients will enter the Host's IP address.

### 2. The Rules of Engagement

* A **Bullseye** card is dealt face up in the center of the table.
* The Dealer yells *"CLICK CLICK"* and the players' cards flip over.
* **QUICK DRAW:** If *any* player's card matches the value of the Bullseye card, the standoff begins. Press the trigger key immediately! The fastest reflex wins the round and takes the pot.
* **HIGH CARD:** If no one's card matches the Bullseye, the tension fizzles out. The player holding the highest value card automatically wins the pot.

### 3. The Penalty for Misfiring

* **Misfire:** If you press the trigger key when there is NO match to the Bullseye, you misfire and lose the round. A tombstone will mark your card.
* **Dealer's Folly:** If the *Dealer* misfires, they do not win the round. Instead, the cards in the pot are randomly dealt and scattered around the table to the other active players.

### ⌨️ Controls

* **`T`** - Pull the Trigger!
* **`S`** - Start Game (Host only)
* **`R`** - Restart / Play Again (Host only)
* **`SPACE`** - Kick open the saloon doors (Proceed past the title screen)

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📜 License

[MIT](https://choosealicense.com/licenses/mit/)

```

Would you like me to draft a quick setup guide for your friends so they know how to connect to your IP address when you host?

```
Additional sounds: Joseph SARDIN - BigSoundBank.com (A single shot of .357 Magnum.)
