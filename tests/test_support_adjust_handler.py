import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class _Message:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


requests_module = ModuleType("requests")
requests_module.post = Mock()
requests_module.Timeout = type("Timeout", (Exception,), {})
requests_module.RequestException = type("RequestException", (Exception,), {})

linebot_module = ModuleType("linebot")
linebot_models_module = ModuleType("linebot.models")
linebot_models_module.TextSendMessage = _Message
linebot_models_module.FlexSendMessage = _Message

with patch.dict(sys.modules, {"requests": requests_module, "linebot": linebot_module,
                              "linebot.models": linebot_models_module}):
    from handlers import support_adjust_handler


class SupportAdjustHandlerTests(unittest.TestCase):
    def setUp(self):
        self.user_id = "test-support-user"
        self.event = SimpleNamespace(reply_token="test-reply-token")
        self.api = Mock()
        support_adjust_handler.clear_session(self.user_id)

    def tearDown(self):
        support_adjust_handler.clear_session(self.user_id)

    def send(self, text):
        return support_adjust_handler.handle_support_adjustment(
            self.event, self.user_id, text, self.api
        )

    def test_department_is_asked_and_sent(self):
        response = Mock()
        response.json.return_value = {"success": True, "row": 31}
        with patch.object(support_adjust_handler.requests, "post", return_value=response) as post:
            for message in ("支援醫師調診單", "測試醫師", "婦產科", "10/30 上午診", "休診", "會議"):
                self.assertTrue(self.send(message))

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["doctor_name"], "測試醫師")
        self.assertEqual(payload["department"], "婦產科")
        self.assertEqual(payload["original_date"], "10/30 上午診")
        self.assertEqual(self.api.reply_message.call_count, 6)
        self.assertIn("科別", self.api.reply_message.call_args_list[1].args[1].text)
        self.assertEqual(support_adjust_handler.get_session(self.user_id), {})

    def test_menu_releases_old_state(self):
        self.send("支援醫師調診單")
        self.send("測試醫師")
        self.assertFalse(self.send("主選單"))
        self.assertEqual(support_adjust_handler.get_session(self.user_id), {})

    def test_application_error_does_not_claim_success(self):
        response = Mock()
        response.json.return_value = {"success": False, "error": "missing_department"}
        with patch.object(support_adjust_handler.requests, "post", return_value=response):
            for message in ("支援醫師調診單", "測試醫師", "婦產科", "10/30 上午診", "休診", "會議"):
                self.send(message)
        reply = self.api.reply_message.call_args.args[1]
        self.assertIn("未能確認", reply.text)
        self.assertEqual(support_adjust_handler.get_session(self.user_id), {})


if __name__ == "__main__":
    unittest.main()
