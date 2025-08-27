from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ancienttrivia_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory state (extend with DB for persistence)
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
    }
]

power_up_effects = {
    'shield': 'skip_question',
    'sword': 'reveal_letter', 
    'potion': 'extra_time'
}

# Store player info: { sid: {username, room, score, powerups_used} }
players = {}

def get_next_question(room):
    """Get a random question that hasn't been asked recently"""
    if 'used_questions' not in rooms[room]:
        rooms[room]['used_questions'] = []
    
    available_questions = [q for q in questions_pool if q not in rooms[room]['used_questions']]
    
    if not available_questions:
        rooms[room]['used_questions'] = []  # Reset if all used
        available_questions = questions_pool
    
    question = random.choice(available_questions)
    rooms[room]['used_questions'].append(question)
    
    # Keep only last 3 questions to avoid immediate repeats
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
    
    # Sort scores in descending order
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    socketio.emit('score_update', sorted_scores, room=room)

def clean_empty_rooms():
    """Remove empty rooms to prevent memory leaks"""
    empty_rooms = [room for room, data in rooms.items() if not data['players']]
    for room in empty_rooms:
        del rooms[room]

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']
    
    # Validate input
    if not username or not room:
        emit('error', 'Username and room are required')
        return
    
    if len(username) > 20:
        emit('error', 'Username too long (max 20 characters)')
        return
        
    join_room(room)
    sid = request.sid
    
    # Initialize room if it doesn't exist
    if room not in rooms:
        rooms[room] = {
            'players': {},
            'current_question': None,
            'answers_received': {},
            'question_start_time': None,
            'used_questions': []
        }
    
    # Check if username is already taken in this room
    existing_usernames = [p['username'] for p in rooms[room]['players'].values()]
    if username in existing_usernames:
        emit('error', 'Username already taken in this room')
        return
    
    # Add player to room and global players dict
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
    
    # Send question logic
    if len(rooms[room]['players']) == 1:
        # First player - start new game
        send_question(room)
    elif rooms[room]['current_question']:
        # Send current question to new player with remaining time
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
    
    # Check for correct answer
    if user_answer == correct_answer and sid not in rooms[room]['answers_received']:
        # Calculate points based on speed (bonus for quick answers)
        time_elapsed = time.time() - rooms[room]['question_start_time'] if rooms[room]['question_start_time'] else 30
        speed_bonus = max(0, 30 - int(time_elapsed)) // 3  # Up to 10 bonus points
        points = 10 + speed_bonus
        
        players[sid]['score'] += points
        rooms[room]['players'][sid]['score'] += points
        rooms[room]['answers_received'][sid] = True
        
        emit('message', f"⚔️ {player['username']} answered correctly! +{points} points.", room=room)
        emit('correct_answer', {'answer': q['answer'], 'lore': q['lore']}, room=room)
        update_scores(room)
        
        # Auto-advance after 3 seconds or when all players answered
        if len(rooms[room]['answers_received']) >= len(rooms[room]['players']):
            socketio.sleep(2)  # Short delay to show the answer
            send_question(room)
    else:
        # Broadcast as chat message if not correct answer
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
    
    # Mark powerup as used
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
        socketio.sleep(3)  # Show answer for 3 seconds
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
    socketio.run(app, debug=True, port=5000)
