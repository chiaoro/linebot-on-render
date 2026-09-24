import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from handlers import meeting_leave_handler
from utils.doctor_info import DoctorDirectoryUnavailable
from utils.state_manager import clear_state, get_state, set_state


def make_event(text):
    return SimpleNamespace(
        message=SimpleNamespace(text=text),
        reply_token="reply-token",
    )


class MeetingLeaveHandlerTests(unittest.TestCase):
    user_id = "test-user"

    def setUp(self):
        clear_state(self.user_id)

    def tearDown(self):
        clear_state(self.user_id)

    @patch.object(meeting_leave_handler, "get_doctor_info")
    def test_temporary_lookup_failure_keeps_reason_state(self, get_doctor_info):
        set_state(self.user_id, "ASK_REASON")
        get_doctor_info.side_effect = DoctorDirectoryUnavailable("temporary")
        line_bot_api = Mock()

        handled = meeting_leave_handler.handle_meeting_leave(
            make_event("休假"), self.user_id, "休假", line_bot_api
        )

        self.assertTrue(handled)
        self.assertEqual(get_state(self.user_id), "ASK_REASON")
        reply = line_bot_api.reply_message.call_args.args[1]
        self.assertIn("直接再傳一次", reply.text)

    @patch.object(meeting_leave_handler, "log_meeting_reply")
    @patch.object(meeting_leave_handler, "get_doctor_info")
    def test_success_clears_reason_state(self, get_doctor_info, log_reply):
        set_state(self.user_id, "ASK_REASON")
        get_doctor_info.return_value = ("測試醫師", "內科")
        line_bot_api = Mock()

        handled = meeting_leave_handler.handle_meeting_leave(
            make_event("休假"), self.user_id, "休假", line_bot_api
        )

        self.assertTrue(handled)
        self.assertIsNone(get_state(self.user_id))
        log_reply.assert_called_once()

    @patch.object(meeting_leave_handler, "log_meeting_reply")
    @patch.object(meeting_leave_handler, "get_doctor_info")
    def test_submission_failure_keeps_reason_state(self, get_doctor_info, log_reply):
        set_state(self.user_id, "ASK_REASON")
        get_doctor_info.return_value = ("測試醫師", "內科")
        log_reply.side_effect = RuntimeError("temporary")
        line_bot_api = Mock()

        meeting_leave_handler.handle_meeting_leave(
            make_event("休假"), self.user_id, "休假", line_bot_api
        )

        self.assertEqual(get_state(self.user_id), "ASK_REASON")
        reply = line_bot_api.reply_message.call_args.args[1]
        self.assertIn("本次尚未完成登記", reply.text)

    @patch.object(meeting_leave_handler, "get_doctor_info")
    def test_missing_binding_clears_state_with_specific_message(self, get_doctor_info):
        set_state(self.user_id, "ASK_REASON")
        get_doctor_info.return_value = (None, None)
        line_bot_api = Mock()

        meeting_leave_handler.handle_meeting_leave(
            make_event("休假"), self.user_id, "休假", line_bot_api
        )

        self.assertIsNone(get_state(self.user_id))
        reply = line_bot_api.reply_message.call_args.args[1]
        self.assertIn("查無您的醫師綁定資料", reply.text)


if __name__ == "__main__":
    unittest.main()
