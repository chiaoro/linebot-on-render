# utils/state_manager.py

# ✅ 簡單的使用者狀態管理
user_states = {}

def set_state(user_id, state):
    user_states[user_id] = state

def get_state(user_id):
    return user_states.get(user_id)

def clear_state(user_id):
    if user_id in user_states:
        del user_states[user_id]
