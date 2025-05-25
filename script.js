const socket = io();

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

const powerUps = {
  shield: document.getElementById('shield'),
  sword: document.getElementById('sword'),
  potion: document.getElementById('potion'),
};

let username, room;
let canSend = true;
let countdownInterval;
let currentTimer = 20;
let usedPowerUps = {
  shield: 0,
  sword: 0,
  potion: 0,
};
let currentAnswer = '';
let revealedLetters = 0;

joinBtn.addEventListener('click', () => {
  username = usernameInput.value.trim();
  room = roomInput.value.trim();
  if (!username || !room) {
    alert('Your warrior name and arena are required.');
    return;
  }
  socket.emit('join_room', { username, room });
});

socket.on('joined', data => {
  loginDiv.style.display = 'none';
  gameDiv.style.display = 'block';
  roomTitle.textContent = `Arena: ${data.room}`;
  addChatMessage(`🛡️ You entered the arena as ${data.username}. Prepare for battle!`);
});

socket.on('message', data => {
  addChatMessage(data);
});

socket.on('new_question', data => {
  currentAnswer = data.answer.toLowerCase();
  revealedLetters = 0;
  questionEl.textContent = data.question;
  resetTimer(data.time || 20);
  loreEl.textContent = data.lore || '';
  canSend = true;
});

socket.on('score_update', scores => {
  updateScores(scores);
});

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
  if (!canSend) return;
  const msg = messageInput.value.trim();
  if (!msg) return;
  socket.emit('answer', msg);
  messageInput.value = '';
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
    li.textContent = `${player}: ${score}`;
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
    if (currentTimer <= 0) {
      clearInterval(countdownInterval);
      canSend = false;
      addChatMessage('⏰ Time is up! Waiting for the next question...');
      socket.emit('time_up');
    }
  }, 1000);
}

// PowerUps
powerUps.shield.addEventListener('click', () => usePowerUp('shield'));
powerUps.sword.addEventListener('click', () => usePowerUp('sword'));
powerUps.potion.addEventListener('click', () => usePowerUp('potion'));

function usePowerUp(type) {
  if (usedPowerUps[type] > 0) {
    alert('Power-up already used for this question.');
    return;
  }
  socket.emit('powerup', type);
  usedPowerUps[type]++;
}

// Reveal a letter on sword power-up
socket.on('reveal_letter', () => {
  if (revealedLetters < currentAnswer.length) {
    revealedLetters++;
    let revealed = currentAnswer
      .split('')
      .map((c, i) => (i < revealedLetters ? c : '_'))
      .join(' ');
    questionEl.textContent = `Hint: ${revealed}`;
  }
});

// Extra time on potion power-up
socket.on('extra_time', extraSeconds => {
  currentTimer += extraSeconds;
  countdownEl.textContent = currentTimer;
});

// Shield skips question
socket.on('skip_question', () => {
  addChatMessage('🛡️ Shield used! Question skipped.');
  canSend = false;
  clearInterval(countdownInterval);
});
