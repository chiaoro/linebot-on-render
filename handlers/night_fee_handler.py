from utils.session_manager import get_session, set_session, clear_session

def handle_night_fee(event, user_id, text, line_bot_api):
    session = get_session(user_id)
    step = session.get("step", 0)

    if text == "夜點費申請":
        set_session(user_id, {"step": 1})
        ...
        return True

    if step == 1:
        ...
        clear_session(user_id)
        return True
