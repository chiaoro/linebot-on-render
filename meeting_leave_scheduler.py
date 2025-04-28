from utils.line_push import push_text_to_group
import os

def run_meeting_leave_scheduler():
    push_text_to_group(os.getenv("All_doctor_group_id"), "📣 請記得回覆本週院務會議是否出席（回覆 Y 或 N）！")
