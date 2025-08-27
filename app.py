from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ancienttrivia_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory state
rooms = {}
questions_pool = [
    {
        'question': 'Which ancient civilization built Machu Picchu?',
        'answer': 'Inca',
        'lore': 'The Inca Empire created Machu Picchu high in the Andes mountains around 1450 AD.'
    },
    {
        'question': 'What is the name of the ancient Egyptian writing system?',
        'answer': 'Hieroglyphics',
        'lore': 'Hieroglyphics combine logographic and alphabetic elements, used for over 3,000 years.'
    },
    {
        'question': 'Who was the Greek god of the underworld?',
        'answer': 'Hades',
        'lore': 'Hades ruled the underworld and was brother to Zeus and Poseidon.'
    },
    {
        'question': 'What massive wall was built to protect ancient China?',
        'answer': 'Great Wall of China',
        'lore': 'The Great Wall spans over 13,000 miles and took centuries to complete.'
    },
    {
        'question': 'Which Roman structure could hold 50,000 spectators?',
        'answer': 'Colosseum',
        'lore': 'The Colosseum hosted gladiatorial contests and public spectacles for 400 years.'
    },
    {
        'question': 'What ancient wonder was located in Alexandria?',
        'answer': 'Lighthouse',
        'lore': 'The Lighthouse of Alexandria was one of the Seven Wonders of the Ancient World.'
    },
    {
        'question': 'Which ancient civilization created the first known legal code?',
        'answer': 'Babylonian',
        'lore': 'Hammurabi\'s Code from Babylon established the principle of "eye for an eye".'
    },
    {
        'question': 'What was the capital of the Byzantine Empire?',
        'answer': 'Constantinople',
        'lore': 'Constantinople, now Istanbul, was the eastern capital of the Roman Empire.'
    }
]

power_up_effects = {
    'shield': 'skip_question',
    'sword': 'reveal_letter', 
    'potion': 'extra_time'
}

players = {}

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ancient Trivia Arena</title>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap" rel="stylesheet" />
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap');

    body {
      margin: 0; padding: 0;
      font-family: 'Cinzel', serif;
      background: url('https://cdn.pixabay.com/photo/2017/10/20/20/59/paper-2877382_1280.jpg') no-repeat center center fixed;
      background-size: cover;
      color: #f7ecd2;
      min-height: 100vh;
    }

    #login, #game {
      max-width: 600px;
      margin: 60px auto;
      background: rgba(47, 35, 17, 0.92);
      padding: 40px;
      border-radius: 15px;
      border: 3px double #bda85f;
      box-shadow: 0 0 60px #a67c00cc;
      animation: fadeIn 2s ease forwards;
    }

    h2, h3 {
      text-align: center;
      color: #f0df8f;
      text-shadow: 1px 1px 4px #6b5300;
    }

    input[type="text"] {
      width: 100%;
      padding: 14px;
      margin: 15px 0;
      border-radius: 8px;
      border: 1.5px solid #d1b954;
      font-size: 18px;
      background: #fff6d0;
      color: #3b2e00;
      box-shadow: inset 0 0 10px #d1b95488;
      transition: 0.3s ease;
      box-sizing: border-box;
    }

    input[type="text"]:focus {
      outline: none;
      border-color: #ffd700;
      box-shadow: 0 0 10px #ffd700aa;
    }

    button {
      width: 100%;
      background-color: #bfa136;
      border: none;
      padding: 16px;
      font-size: 20px;
      border-radius: 10px;
      cursor: pointer;
      color: #372b00;
      font-weight: 700;
      transition: background-color 0.3s, transform 0.25s;
      box-shadow: 0 0 15px #bfa136aa;
    }

    button:hover {
      background-color: #e8d15c;
      transform: scale(1.07);
      box-shadow: 0 0 20px #ffe600cc;
    }

    #game header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
    }

    #timer {
      font-family: 'Papyrus', fantasy;
      font-size: 18px;
      color: #ffd700;
      text-shadow: 0 0 8px #bfa136cc;
      animation: pulse 2s infinite alternate;
    }

    #questionBox {
      background-color: #4d3c17cc;
      border-radius: 12px;
      padding: 25px;
      margin: 25px 0;
      text-align: center;
      font-size: 24px;
      font-weight: 600;
      color: #fff9d3;
      box-shadow: 0 0 25px #bfa136bb;
      animation: glow 3s infinite alternate;
      min-height: 90px;
    }

    #powerUps {
      margin-top: 15px;
      display: flex;
      justify-content: center;
      gap: 20px;
    }

    .powerup {
      font-size: 34px;
      background: transparent;
      border: none;
      cursor: pointer;
      transition: transform 0.3s;
      color: #d1b954;
      filter: drop-shadow(0 0 3px #a67c00);
      padding: 10px;
    }

    .powerup:hover {
      transform: scale(1.4) rotate(10deg);
      color: #ffd700;
      filter: drop-shadow(0 0 12px #ffd700);
    }

    .powerup.used {
      opacity: 0.3;
      pointer-events: none;
    }

    #chatArea {
      margin-bottom: 30px;
    }

    #chat {
      background: #fff8dccc;
      color: #3e2e00;
      height: 180px;
      overflow-y: auto;
      padding: 15px;
      border-radius: 10px;
      font-family: 'Courier New', monospace;
      font-size: 16px;
      border: 1.5px solid #bfa136aa;
      box-shadow: inset 0 0 10px #bfa13688;
    }

    #messageContainer {
      display: flex;
      gap: 0;
    }

    #message {
      flex: 1;
      padding: 14px;
      font-size: 18px;
      border-radius: 10px 0 0 10px;
      border: 1.5px solid #d1b954;
      border-right: none;
      box-shadow: inset 0 0 10px #d1b95488;
      color: #3b2e00;
    }

    #sendBtn {
      width: 100px;
      border-radius: 0 10px 10px 0;
      background-color: #bfa136;
      font-weight: 700;
      transition: background-color 0.3s;
    }

    #sendBtn:hover {
      background-color: #ffd700;
      color: #372b00;
    }

    #scoresArea {
      background: #fff8dcaa;
      border-radius: 12px;
      padding: 15px 25px;
      color: #4a3600;
      font-weight: 600;
      box-shadow: 0 0 15px #bfa13688;
      max-height: 140px;
      overflow-y: auto;
    }

    #scoresArea ul {
      list-style-type: none;
      padding-left: 0;
      margin: 0;
    }

    #scoresArea li {
      padding: 6px 0;
      border-bottom: 1px solid #d1b954aa;
    }

    #lore {
      margin-top: 25px;
      font-style: italic;
      font-family: 'Georgia', serif;
      color: #f4e7a8cc;
      text-align: center;
      font-size: 16px;
      min-height: 40px;
    }

    #footerQuote {
      margin-top: 40px;
      font-size: 14px;
      font-style: italic;
      text-align: center;
      color: #d9c98c;
      text-shadow: 0 0 5px #bfa136cc;
    }

    .error {
      background-color: #d73327;
      color: white;
      padding: 10px;
      border-radius: 5px;
      margin: 10px 0;
      text-align: center;
    }

    @keyframes glow {
      from { box-shadow: 0 0 15px #ffd700cc; }
      to { box-shadow: 0 0 40px #ffd700ff; }
    }

    @keyframes pulse {
      0% { transform: scale(1); opacity: 0.8; }
      50% { transform: scale(1.1); opacity: 1; }
      100% { transform: scale(1); opacity: 0.8; }
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @media (max-width: 768px) {
      #login, #game { 
        margin: 20px; 
        padding: 20px; 
      }
      #game header { 
        flex-direction: column; 
        gap: 10px; 
      }
      #questionBox { 
        font-size: 20px; 
      }
      .powerup { 
        font-size: 28px; 
      }
    }
  </style>
</head>
<body>
  <div id="login">
    <h2>🏛️ Enter the Ancient Arena</h2>
    <div id="errorDiv"></div>
    <input type="text" id="username" placeholder="Your Warrior Name" maxlength="20" />
    <input type="text" id="room" placeholder="Arena Name" />
    <button id="joinBtn">⚔️ Join Battle</button>
  </div>

  <div id="game" style="display:none;">
    <header>
      <h2 id="roomTitle">Arena</h2>
      <div id="timer">Time Left: <span id="countdown">--</span>s</div>
    </header>
    
    <section id="questionBox">
      <div id="question">The Oracle is preparing your challenge...</div>
      <div id="powerUps">
        <button class="powerup" id="shield" title="Shield of Wisdom (Skip question)">🛡️</button>
        <button class="powerup" id="sword" title="Sword of Truth (Reveal letter)">🗡️</button>
        <button class="powerup" id="potion" title="Potion of Focus (Extra time)">🧪</button>
      </div>
    </section>
    
    <section id="chatArea">
      <div id="chat"></div>
      <div id="messageContainer">
        <input type="text" id="message" placeholder="Answer or chat here..." autocomplete="off" />
        <button id="sendBtn">Send</button>
      </div>
    </section>
    
    <section id="scoresArea">
      <h3>🏆 Scores</h3>
      <ul id="scores"></ul>
    </section>
    
    <footer>
      <div id="lore"></div>
      <div id="footerQuote">"Only the worthy shall triumph in the arena of knowledge."</div>
    </footer>
  </div>

  <script src="https://cdn.socket.io/4.5.1/socket.io.min.js"></script>
  <script>
    const socket = io();

    // DOM Elements
    const loginDiv = document.getElementById('login');
    const gameDiv = document.getElementById('game');
    const joinBtn = document.getElementById('joinBtn');
    const usernameInput = document.getElementById('username');
    const roomInput = document.getElementById('room');
    const roomTitle = document.getElementById('roomTitle');
    const countdownEl = document.getElementById('countdown');
    const questionEl = document.getElementById('question');
    const chatEl = document.getElementById('chat');
    const messageInput = document.getElementById('message');
    const sendBtn = document.getElementById('sendBtn');
    const scoresList = document.getElementById('scores');
    const loreEl = document.getElementById('lore');
    const errorDiv = document.getElementById('errorDiv');

    const powerUps = {
      shield: document.getElementById('shield'),
      sword: document.getElementById('sword'),
      potion: document.getElementById('potion'),
    };

    // Game State
    let username, room;
    let canSend = true;
    let countdownInterval;
    let currentTimer = 30;
    let currentAnswer = '';
    let revealedLetters = 0;
    let usedPowerUps = new Set();

    // Event Listeners
    joinBtn.addEventListener('click', joinRoom);
    usernameInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') joinRoom();
    });
    roomInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') joinRoom();
    });

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') sendMessage();
    });

    powerUps.shield.addEventListener('click', () => usePowerUp('shield'));
    powerUps.sword.addEventListener('click', () => usePowerUp('sword'));
    powerUps.potion.addEventListener('click', () => usePowerUp('potion'));

    // Functions
    function joinRoom() {
      username = usernameInput.value.trim();
      room = roomInput.value.trim();
      
      if (!username || !room) {
        showError('Your warrior name and arena are required.');
        return;
      }
      
      if (username.length > 20) {
        showError('Warrior name too long (max 20 characters).');
        return;
      }
      
      socket.emit('join_room', { username, room });
    }

    function sendMessage() {
      if (!canSend) return;
      const msg = messageInput.value.trim();
      if (!msg) return;
      socket.emit('answer', msg);
      messageInput.value = '';
    }

    function usePowerUp(type) {
      if (usedPowerUps.has(type)) {
        addChatMessage('⚠️ Power-up already used for this question.');
        return;
      }
      socket.emit('powerup', type);
      usedPowerUps.add(type);
      powerUps[type].classList.add('used');
    }

    function showError(message) {
      errorDiv.innerHTML = `<div class="error">${message}</div>`;
      setTimeout(() => {
        errorDiv.innerHTML = '';
      }, 3000);
    }

    function addChatMessage(msg) {
      const p = document.createElement('p');
      p.innerHTML = msg;
      chatEl.appendChild(p);
      chatEl.scrollTop = chatEl.scrollHeight;
    }

    function updateScores(scores) {
      scoresList.innerHTML = '';
      for (const [player, score] of Object.entries(scores)) {
        const li = document.createElement('li');
        li.textContent = `${player}: ${score} points`;
        scoresList.appendChild(li);
      }
    }

    function resetTimer(time) {
      clearInterval(countdownInterval);
      currentTimer = time;
      countdownEl.textContent = currentTimer;
      
      countdownInterval = setInterval(() => {
        currentTimer--;
        countdownEl.textContent = currentTimer;
        
        // Timer color changes
        if (currentTimer <= 5) {
          countdownEl.style.color = '#ff4444';
        } else if (currentTimer <= 10) {
          countdownEl.style.color = '#ffaa00';
        } else {
          countdownEl.style.color = '#ffd700';
        }
        
        if (currentTimer <= 0) {
          clearInterval(countdownInterval);
          canSend = false;
          addChatMessage('⏰ Time is up! Waiting for the next question...');
          socket.emit('time_up');
        }
      }, 1000);
    }

    function resetPowerUps() {
      usedPowerUps.clear();
      Object.values(powerUps).forEach(btn => {
        btn.classList.remove('used');
      });
    }

    // Socket Event Handlers
    socket.on('joined', data => {
      loginDiv.style.display = 'none';
      gameDiv.style.display = 'block';
      roomTitle.textContent = `🏛️ Arena: ${data.room}`;
      addChatMessage(`🛡️ You entered the arena as ${data.username}. Prepare for battle!`);
    });

    socket.on('error', message => {
      showError(message);
    });

    socket.on('message', data => {
      addChatMessage(data);
    });

    socket.on('new_question', data => {
      currentAnswer = data.question.toLowerCase();
      revealedLetters = 0;
      questionEl.textContent = data.question;
      loreEl.textContent = data.lore || '';
      resetTimer(data.time || 30);
      resetPowerUps();
      canSend = true;
      
      // Add visual feedback for new question
      questionEl.style.animation = 'none';
      setTimeout(() => {
        questionEl.style.animation = 'glow 3s infinite alternate';
      }, 10);
    });

    socket.on('score_update', scores => {
      updateScores(scores);
    });

    socket.on('correct_answer', data => {
      addChatMessage(`✅ Correct! The answer was: ${data.answer}`);
      addChatMessage(`📜 ${data.lore}`);
      canSend = false;
    });

    socket.on('time_up_reveal', data => {
      addChatMessage(`⏰ Time's up! The answer was: ${data.answer}`);
      addChatMessage(`📜 ${data.lore}`);
      canSend = false;
    });

    socket.on('reveal_letter', () => {
      if (revealedLetters < currentAnswer.length) {
        revealedLetters++;
        let revealed = currentAnswer
          .split('')
          .map((c, i) => (i < revealedLetters ? c.toUpperCase() : '_'))
          .join(' ');
        questionEl.innerHTML = `<div style="margin-bottom: 10px;">${questionEl.textContent}</div><div style="font-size: 18px; color: #ffd700;">Hint: ${revealed}</div>`;
      }
    });

    socket.on('extra_time', extraSeconds => {
      currentTimer += extraSeconds;
      countdownEl.textContent = currentTimer;
      addChatMessage(`🧪 Extra time granted! +${extraSeconds} seconds!`);
    });

    socket.on('skip_question', () => {
      addChatMessage('🛡️ Question skipped by Shield of Wisdom!');
      canSend = false;
      clearInterval(countdownInterval);
    });

    // Initialize
    messageInput.focus();
  </script>
</body>
</html>
'''

def get_next_question(room):
    """Get a random question that hasn't been asked recently"""
    if 'used_questions' not in rooms[room]:
        rooms[room]['used_questions'] = []
    
    available_questions = [q for q in questions_pool if q not in rooms[room]['used_questions']]
    
    if not available_questions:
        rooms[room]['used_questions'] = []
        available_questions = questions_pool
    
    question = random.choice(available_questions)
    rooms[room]['used_questions'].append(question)
    
    if len(rooms[room]['used_questions']) > 3:
        rooms[room]['used_questions'].pop(0)
    
    return question

def send_question(room):
    """Send a new question to all players in the room"""
    if room not in rooms:
        return
        
    q = get_next_question(room)
    rooms[room]['current_question'] = q
    rooms[room]['answers_received'] = {}
    rooms[room]['question_start_time'] = time.time()
    
    # Reset powerups for new question
    for player_id in rooms[room]['players']:
        if player_id in players:
            players[player_id]['powerups_used'] = set()
    
    socketio.emit('new_question', {
        'question': q['question'],
        'lore': q['lore'],
        'time': 30
    }, room=room)

def update_scores(room):
    """Update and broadcast scores to all players in room"""
    if room not in rooms:
        return
        
    scores = {}
    for player_id, player_data in rooms[room]['players'].items():
        scores[player_data['username']] = player_data['score']
    
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    socketio.emit('score_update', sorted_scores, room=room)

def clean_empty_rooms():
    """Remove empty rooms to prevent memory leaks"""
    empty_rooms = [room for room, data in rooms.items() if not data['players']]
    for room in empty_rooms:
        del rooms[room]

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']
    
    if not username or not room:
        emit('error', 'Username and room are required')
        return
    
    if len(username) > 20:
        emit('error', 'Username too long (max 20 characters)')
        return
        
    join_room(room)
    sid = request.sid
    
    if room not in rooms:
        rooms[room] = {
            'players': {},
            'current_question': None,
            'answers_received': {},
            'question_start_time': None,
            'used_questions': []
        }
    
    existing_usernames = [p['username'] for p in rooms[room]['players'].values()]
    if username in existing_usernames:
        emit('error', 'Username already taken in this room')
        return
    
    rooms[room]['players'][sid] = {
        'username': username, 
        'score': 0, 
        'powerups_used': set()
    }
    players[sid] = {
        'username': username, 
        'room': room, 
        'score': 0, 
        'powerups_used': set()
    }
    
    emit('joined', {'username': username, 'room': room})
    emit('message', f"🛡️ {username} has entered the arena!", room=room)
    
    if len(rooms[room]['players']) == 1:
        send_question(room)
    elif rooms[room]['current_question']:
        time_elapsed = time.time() - rooms[room]['question_start_time'] if rooms[room]['question_start_time'] else 0
        time_remaining = max(1, 30 - int(time_elapsed))
        
        emit('new_question', {
            'question': rooms[room]['current_question']['question'],
            'lore': rooms[room]['current_question']['lore'],
            'time': time_remaining
        })
    
    update_scores(room)

@socketio.on('answer')
def handle_answer(msg):
    sid = request.sid
    if sid not in players:
        return
    
    player = players[sid]
    room = player['room']
    
    if room not in rooms or not rooms[room]['current_question']:
        return
    
    q = rooms[room]['current_question']
    correct_answer = q['answer'].lower().strip()
    user_answer = msg.lower().strip()
    
    if user_answer == correct_answer and sid not in rooms[room]['answers_received']:
        time_elapsed = time.time() - rooms[room]['question_start_time'] if rooms[room]['question_start_time'] else 30
        speed_bonus = max(0, 30 - int(time_elapsed)) // 3
        points = 10 + speed_bonus
        
        players[sid]['score'] += points
        rooms[room]['players'][sid]['score'] += points
        rooms[room]['answers_received'][sid] = True
        
        emit('message', f"⚔️ {player['username']} answered correctly! +{points} points.", room=room)
        emit('correct_answer', {'answer': q['answer'], 'lore': q['lore']}, room=room)
        update_scores(room)
        
        if len(rooms[room]['answers_received']) >= len(rooms[room]['players']):
            socketio.sleep(2)
            send_question(room)
    else:
        emit('message', f"{player['username']}: {msg}", room=room)

@socketio.on('powerup')
def handle_powerup(powerup):
    sid = request.sid
    if sid not in players:
        return
    
    player = players[sid]
    room = player['room']
    
    if powerup not in power_up_effects:
        return
    
    if powerup in player['powerups_used']:
        emit('message', f"🛡️ {player['username']} already used {powerup} for this question.", room=sid)
        return
    
    player['powerups_used'].add(powerup)
    if sid in rooms[room]['players']:
        rooms[room]['players'][sid]['powerups_used'].add(powerup)
    
    effect = power_up_effects[powerup]
    
    if effect == 'skip_question':
        emit('message', f"🛡️ {player['username']} used Shield of Wisdom! Question skipped.", room=room)
        socketio.sleep(1)
        send_question(room)
    elif effect == 'reveal_letter':
        emit('message', f"🗡️ {player['username']} used Sword of Truth! A letter is revealed.", room=room)
        emit('reveal_letter', room=room)
    elif effect == 'extra_time':
        emit('message', f"🧪 {player['username']} used Potion of Focus! +15 seconds for everyone.", room=room)
        emit('extra_time', 15, room=room)

@socketio.on('time_up')
def handle_time_up():
    sid = request.sid
    if sid not in players:
        return
    
    room = players[sid]['room']
    if room in rooms and rooms[room]['current_question']:
        q = rooms[room]['current_question']
        emit('time_up_reveal', {'answer': q['answer'], 'lore': q['lore']}, room=room)
        socketio.sleep(3)
        send_question(room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in players:
        player = players[sid]
        room = player['room']
        
        if room in rooms and sid in rooms[room]['players']:
            username = rooms[room]['players'][sid]['username']
            del rooms[room]['players'][sid]
            emit('message', f"💀 {username} has fallen and left the arena.", room=room)
            update_scores(room)
        
        del players[sid]
        clean_empty_rooms()

if __name__ == '__main__':
    print("🏛️ Ancient Trivia Arena is starting...")
    print("📍 Open your browser and go to: http://localhost:5000")
    print("⚔️ May the wisest warrior prevail!")
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
