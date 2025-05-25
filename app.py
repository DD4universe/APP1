from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ancienttrivia_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory state (extend with DB for persistence)
rooms = {}
questions_pool = [
    {
        'question': 'Which ancient civilization built the Machu Picchu?',
        'answer': 'Inca',
        'lore': 'The Inca Empire created Machu Picchu high in the Andes mountains.'
    },
    {
        'question': 'What is the name of the ancient Egyptian writing system?',
        'answer': 'Hieroglyphics',
        'lore': 'Hieroglyphics combine logographic and alphabetic elements.'
    },
    {
        'question': 'Who was the Greek god of the underworld?',
        'answer': 'Hades',
        'lore': 'Hades ruled the underworld and was brother of Zeus.'
    }
]

power_up_effects = {
    'shield': 'skip_question',
    'sword': 'reveal_letter',
    'potion': 'extra_time'
}

# Store player info: { sid: {username, room, score, powerups_used} }
players = {}

def send_question(room):
    q = random.choice(questions_pool)
    rooms[room]['current_question'] = q
    rooms[room]['answers_received'] = {}
    rooms[room]['powerups_used'] = {}
    socketio.emit('new_question', {
        'question': q['question'],
        'answer': q['answer'],
        'lore': q['lore'],
        'time': 20
    }, room=room)

def update_scores(room):
    scores = {p['username']: p['score'] for p in rooms[room]['players'].values()}
    socketio.emit('score_update', scores, room=room)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    sid = request.sid
    if room not in rooms:
        rooms[room] = {
            'players': {},
            'current_question': None,
            'answers_received': {},
            'powerups_used': {}
        }
    rooms[room]['players'][sid] = {'username': username, 'score': 0, 'powerups_used': set()}
    players[sid] = {'username': username, 'room': room, 'score': 0, 'powerups_used': set()}
    emit('joined', {'username': username, 'room': room}, room=sid)
    emit('message', f"🛡️ {username} has entered the arena!", room=room)
    if len(rooms[room]['players']) == 1:
        send_question(room)
    else:
        # Send current question to new player
        q = rooms[room]['current_question']
        if q:
            emit('new_question', q, room=sid)
    update_scores(room)

@socketio.on('answer')
def handle_answer(msg):
    sid = request.sid
    if sid not in players:
        return
    player = players[sid]
    room = player['room']
    q = rooms[room]['current_question']
    if not q:
        return
    correct_answer = q['answer'].lower()
    if msg.lower() == correct_answer and sid not in rooms[room]['answers_received']:
        players[sid]['score'] += 10
        rooms[room]['answers_received'][sid] = True
        emit('message', f"⚔️ {player['username']} answered correctly! +10 points.", room=room)
        update_scores(room)

        # Check if all players answered or max players answered -> next question
        if len(rooms[room]['answers_received']) == len(rooms[room]['players']):
            send_question(room)
    else:
        # Broadcast chat message
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

    effect = power_up_effects[powerup]
    if effect == 'skip_question':
        emit('skip_question', room=room)
        send_question(room)
    elif effect == 'reveal_letter':
        emit('reveal_letter', room=room)
    elif effect == 'extra_time':
        emit('extra_time', 10, room=room)

@socketio.on('time_up')
def handle_time_up():
    sid = request.sid
    if sid not in players:
        return
    room = players[sid]['room']
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
            del players[sid]
            emit('message', f"💀 {username} has fallen and left the arena.", room=room)
            update_scores(room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
