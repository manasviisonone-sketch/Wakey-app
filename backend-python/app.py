from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from agent import WakeyAgent
import json
import os

# ============================
# 💾 PERSISTENCE LAYER
# ============================

DATA_FILE = "data.json"

def load_db():
    """Load database from JSON file with error handling."""
    if not os.path.exists(DATA_FILE):
        return {
            "users": [],
            "friendRequests": [],
            "friendships": [],
            "alarms": []
        }
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {
                    "users": [],
                    "friendRequests": [],
                    "friendships": [],
                    "alarms": []
                }
            return json.loads(content)
    except json.JSONDecodeError:
        print("⚠️  Warning: data.json is corrupted. Starting with fresh data.")
        return {
            "users": [],
            "friendRequests": [],
            "friendships": [],
            "alarms": []
        }

def save_db():
    """Persist all data to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump({
            "users": users,
            "friendRequests": friend_requests,
            "friendships": friendships,
            "alarms": alarms
        }, f, indent=2)

# ============================
# 🧠 LOAD DATA ON STARTUP
# ============================

_db = load_db()

users = _db["users"]
friend_requests = _db["friendRequests"]
friendships = _db["friendships"]
alarms = _db["alarms"]

# Initialize Flask app
app = Flask(__name__)

# Configure CORS properly
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Initialize agent
agent = WakeyAgent()

# Create data file if it doesn't exist
if not os.path.exists(DATA_FILE):
    save_db()
    print("✅ Created data.json file")
else:
    print(f"✅ Loaded {len(users)} users, {len(friend_requests)} requests, {len(friendships)} friendships, {len(alarms)} alarms")

# ============================================
# 🔐 AUTHENTICATION ROUTES
# ============================================

@app.route('/')
def home():
    """Health check endpoint."""
    return jsonify({
        'message': '🎉 Wakey API v3.0 - Production',
        'status': 'running',
        'version': '3.0.0'
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    """Create a new user account."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'})

    existing = next((u for u in users if u['username'].lower() == username.lower()), None)
    if existing:
        return jsonify({'success': False, 'message': 'Username already taken'})

    new_user = {
        'id': len(users) + 1,
        'username': username,
        'password': password,
        'createdAt': datetime.now().isoformat()
    }

    users.append(new_user)
    save_db()

    return jsonify({
        'success': True,
        'message': 'Account created successfully',
        'user': {'id': new_user['id'], 'username': new_user['username']}
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user login."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'})

    user = next(
        (u for u in users if u['username'].lower() == username.lower() and u['password'] == password),
        None
    )

    if not user:
        return jsonify({'success': False, 'message': 'Invalid username or password'})

    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {'id': user['id'], 'username': user['username']}
    })

# ============================================
# 👥 FRIEND SYSTEM
# ============================================

@app.route('/api/users/search')
def search_users():
    """Search for users by username."""
    query = request.args.get('query', '').strip()
    current_user_id = int(request.args.get('currentUserId', 0))

    if not query:
        return jsonify([])

    return jsonify([
        {'id': u['id'], 'username': u['username']}
        for u in users
        if query.lower() in u['username'].lower() and u['id'] != current_user_id
    ])

@app.route('/api/friends/request', methods=['POST'])
def send_friend_request():
    """Send a friend request."""
    data = request.json
    from_user_id = data.get('fromUserId')
    to_user_id = data.get('toUserId')

    if not from_user_id or not to_user_id:
        return jsonify({'success': False, 'message': 'Invalid user IDs'})

    # Check if already friends
    already_friends = next(
        (f for f in friendships
         if (f['user1Id'] == from_user_id and f['user2Id'] == to_user_id)
         or (f['user1Id'] == to_user_id and f['user2Id'] == from_user_id)),
        None
    )

    if already_friends:
        return jsonify({'success': False, 'message': 'Already friends'})

    # Check if request already exists
    existing_request = next(
        (r for r in friend_requests
         if r['fromUserId'] == from_user_id and r['toUserId'] == to_user_id and r['status'] == 'pending'),
        None
    )

    if existing_request:
        return jsonify({'success': False, 'message': 'Friend request already sent'})

    request_obj = {
        'id': len(friend_requests) + 1,
        'fromUserId': from_user_id,
        'toUserId': to_user_id,
        'status': 'pending',
        'createdAt': datetime.now().isoformat()
    }

    friend_requests.append(request_obj)
    save_db()
    
    return jsonify({'success': True, 'message': 'Friend request sent'})

@app.route('/api/friends/requests/<int:user_id>')
def get_friend_requests(user_id):
    """Get pending friend requests for a user."""
    pending = [
        {
            'id': r['id'],
            'fromUserId': r['fromUserId'],
            'fromUsername': next((u['username'] for u in users if u['id'] == r['fromUserId']), 'Unknown'),
            'createdAt': r['createdAt']
        }
        for r in friend_requests
        if r['toUserId'] == user_id and r['status'] == 'pending'
    ]
    
    return jsonify(pending)

@app.route('/api/friends/accept', methods=['POST'])
def accept_friend_request():
    """Accept a friend request."""
    data = request.json
    request_id = data.get('requestId')
    user_id = data.get('userId')

    if not request_id or not user_id:
        return jsonify({'success': False, 'message': 'Invalid request'})

    req = next((r for r in friend_requests if r['id'] == request_id), None)

    if not req:
        return jsonify({'success': False, 'message': 'Request not found'})

    if req['toUserId'] != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized'})

    req['status'] = 'accepted'

    friendships.append({
        'id': len(friendships) + 1,
        'user1Id': req['fromUserId'],
        'user2Id': req['toUserId'],
        'createdAt': datetime.now().isoformat()
    })

    save_db()

    return jsonify({'success': True, 'message': 'Friend request accepted'})

@app.route('/api/friends/<int:user_id>')
def get_friends(user_id):
    """Get all friends for a user."""
    result = []

    for f in friendships:
        if f['user1Id'] == user_id or f['user2Id'] == user_id:
            friend_id = f['user2Id'] if f['user1Id'] == user_id else f['user1Id']
            friend = next((u for u in users if u['id'] == friend_id), None)
            if friend:
                result.append({'id': friend['id'], 'username': friend['username']})

    return jsonify(result)

# ============================================
# ⏰ ALARM SYSTEM
# ============================================

@app.route('/api/alarms', methods=['POST'])
def create_alarm():
    """Create a new shared alarm."""
    data = request.json
    user_id = data.get('userId')
    friend_id = data.get('friendId')
    time = data.get('time')
    label = data.get('label', 'Wake up!')
    sound = data.get('sound', 'baddie')
    tone = data.get('tone', None)  # Optional: soft, playful, strict

    if not user_id or not friend_id or not time:
        return jsonify({'success': False, 'message': 'Missing required fields'})

    allowed_sounds = ['baddie', 'manifestation', 'getshitdone']
    if sound not in allowed_sounds:
        sound = 'baddie'

    # Validate tone if provided
    if tone and tone not in ['soft', 'playful', 'strict']:
        tone = None

    # Check if users are friends
    are_friends = next(
        (f for f in friendships
         if (f['user1Id'] == user_id and f['user2Id'] == friend_id)
         or (f['user1Id'] == friend_id and f['user2Id'] == user_id)),
        None
    )

    if not are_friends:
        return jsonify({'success': False, 'message': 'Can only create alarms with friends'})

    new_alarm = {
        'id': len(alarms) + 1,
        'user1Id': user_id,
        'user2Id': friend_id,
        'time': time,
        'label': label,
        'sound': sound,
        'tone': tone,
        'isActive': True,
        'snoozeCount': {
            str(user_id): 0,
            str(friend_id): 0
        },
        'acknowledged': [],
        'cancelledBy': None,
        'agentMessage': '',
        'agentTone': '',
        'cancelNotifyMessage': '',
        'createdAt': datetime.now().isoformat()
    }

    alarms.append(new_alarm)
    save_db()
    
    return jsonify({'success': True, 'alarm': new_alarm})

@app.route('/api/alarms/<int:user_id>')
def get_alarms(user_id):
    """Get all active alarms for a user."""
    user_alarms = [
        a for a in alarms 
        if (a['user1Id'] == user_id or a['user2Id'] == user_id) and a.get('isActive', True)
    ]
    return jsonify(user_alarms)

# ============================================
# 🤖 AI AGENT ROUTES
# ============================================

@app.route('/api/agent/acknowledge', methods=['POST'])
def agent_acknowledge():
    """Acknowledge an alarm (mark as awake)."""
    data = request.json
    alarm_id = data.get('alarmId')
    user_id = data.get('userId')

    if not alarm_id or not user_id:
        return jsonify({'success': False, 'message': 'Missing alarmId or userId'})

    alarm = next((a for a in alarms if a['id'] == alarm_id), None)
    if not alarm:
        return jsonify({'success': False, 'message': 'Alarm not found'})

    updated_alarm = agent.acknowledge_alarm(alarm, user_id)
    
    # Update alarm in list
    for i, a in enumerate(alarms):
        if a['id'] == alarm_id:
            alarms[i] = updated_alarm
            break
    
    save_db()
    
    return jsonify({'success': True, 'alarm': updated_alarm})

@app.route('/api/agent/snooze', methods=['POST'])
def agent_snooze():
    """Snooze an alarm."""
    data = request.json
    alarm_id = data.get('alarmId')
    user_id = data.get('userId')

    if not alarm_id or not user_id:
        return jsonify({'success': False, 'message': 'Missing alarmId or userId'})

    alarm = next((a for a in alarms if a['id'] == alarm_id), None)

    if not alarm:
        return jsonify({'success': False, 'message': 'Alarm not found'})

    updated_alarm = agent.snooze_alarm(alarm, user_id)
    
    # Update alarm in list
    for i, a in enumerate(alarms):
        if a['id'] == alarm_id:
            alarms[i] = updated_alarm
            break
    
    save_db()

    return jsonify({'success': True, 'alarm': updated_alarm})

@app.route('/api/agent/cancel', methods=['POST'])
def agent_cancel():
    """Cancel an alarm."""
    data = request.json
    alarm_id = data.get('alarmId')
    user_id = data.get('userId')

    if not alarm_id or not user_id:
        return jsonify({'success': False, 'message': 'Missing alarmId or userId'})

    alarm = next((a for a in alarms if a['id'] == alarm_id), None)

    if not alarm:
        return jsonify({'success': False, 'message': 'Alarm not found'})

    updated_alarm = agent.cancel_alarm(alarm, user_id)
    
    # Update alarm in list
    for i, a in enumerate(alarms):
        if a['id'] == alarm_id:
            alarms[i] = updated_alarm
            break
    
    save_db()

    return jsonify({'success': True, 'alarm': updated_alarm})

# ============================================
# 🧪 DEBUG (DEVELOPMENT ONLY)
# ============================================

@app.route('/api/debug')
def debug():
    """Debug endpoint - shows all data (remove in production)."""
    return jsonify({
        'users': users,
        'friendRequests': friend_requests,
        'friendships': friendships,
        'alarms': alarms
    })


# ============================================
# 🚀 MAIN
# ============================================
if __name__ == '__main__':
    import os
    print("🚀 Wakey API v3.0 - Production Ready")
    print("=" * 50)
    port = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=port, debug=False)