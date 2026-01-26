import json
import os
import sys
import uuid
from datetime import datetime

DB_PATH = 'users.json'

def add_user(username, password, name):
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r') as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                users = []
    else:
        users = []

    if any(u['username'] == username for u in users):
        print(f"Error: User '{username}' already exists.")
        return

    new_user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password": password, 
        "name": name,
        "created_at": datetime.now().isoformat()
    }

    users.append(new_user)

    with open(DB_PATH, 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"User '{username}' added successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('Usage: python add_user.py <username> <password> <"Name">')
        sys.exit(1)
    
    add_user(sys.argv[1], sys.argv[2], sys.argv[3])
