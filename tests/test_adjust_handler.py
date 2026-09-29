import unittest
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import Mock, patch


class _Message:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


requests_module = ModuleType("requests")
requests_module.post = Mock()

linebot_module = ModuleType("linebot")
linebot_models_module = ModuleType("linebot.models")
linebot_models_module.TextSendMessage = _Message
linebot_models_module.FlexSendMessage = _Message

doctor_info_module = ModuleType("utils.doctor_info")
doctor_info_module.get_doctor_info = Mock()

adjust_bubble_module = ModuleType("utils.adjust_bubble")
adjust_bubble_module.get_adjustment_bubble = Mock()

with patch.dict(
    sys.modules,
    {
        "requests": requests_module,
        "linebot": linebot_module,
        "linebot.models": linebot_models_module,
        "utils.doctor_info": doctor_info_module,
        "utils.adjust_bubble": adjust_bubble_module,
    },
):
    from handlers import adjust_handler


class AdjustHandlerTests(unittest.TestCase):
    def setUp(self):
        self.event = SimpleNamespace(reply_token="reply-token")
        self.line_bot_api = Mock()
        self.user_id = "test-user"

    @patch.object(adjust_handler, "set_state")
    @patch.object(adjust_handler, "get_state", return_value=None)
    def test_trigger_starts_flow_with_reply_message(self, _get_state, set_state):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "我要調診", self.line_bot_api
        )

        self.assertTrue(handled)
        set_state.assert_called_once_with(
            self.user_id, {"step": 0, "type": "我要調診"}
        )
        self.line_bot_api.reply_message.assert_called_once()
        self.line_bot_api.push_message.assert_not_called()

    @patch.object(adjust_handler, "get_state", return_value=None)
    def test_unrelated_message_is_not_handled(self, _get_state):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "一般訊息", self.line_bot_api
        )

        self.assertFalse(handled)
        self.line_bot_api.reply_message.assert_not_called()

    @patch.object(adjust_handler, "clear_state")
    @patch.object(
        adjust_handler,
        "get_state",
        return_value={"step": 0, "type": "我要調診"},
    )
    def test_menu_command_clears_state_and_releases_message(
        self, _get_state, clear_state
    ):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "主選單", self.line_bot_api
        )

        self.assertFalse(handled)
        clear_state.assert_called_once_with(self.user_id)
        self.line_bot_api.reply_message.assert_not_called()

    @patch.object(adjust_handler, "set_state")
    @patch.object(
        adjust_handler,
        "get_state",
        return_value={"step": 0, "type": "我要調診"},
    )
    def test_valid_original_date_advances_flow(self, _get_state, set_state):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "10/2 上午診", self.line_bot_api
        )

        self.assertTrue(handled)
        saved_state = set_state.call_args.args[1]
        self.assertEqual(saved_state["step"], 1)
        self.assertEqual(saved_state["original_date"], "10/2 上午診")
        self.line_bot_api.reply_message.assert_called_once()

    @patch.object(
        adjust_handler,
        "get_state",
        return_value={"step": 0, "type": "我要調診"},
    )
    def test_invalid_original_date_replies_without_advancing(self, _get_state):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "日期不確定", self.line_bot_api
        )

        self.assertTrue(handled)
        reply = self.line_bot_api.reply_message.call_args.args[1]
        self.assertIn("格式錯誤", reply.text)

    @patch.object(adjust_handler, "clear_state")
    @patch.object(adjust_handler, "get_adjustment_bubble", return_value={"type": "bubble"})
    @patch.object(adjust_handler, "get_doctor_info", return_value=("測試醫師", "測試科"))
    @patch.object(adjust_handler.requests, "post")
    @patch.object(
        adjust_handler,
        "get_state",
        return_value={
            "step": 2,
            "type": "我要調診",
            "original_date": "10/2 上午診",
            "new_date": "10/3 下午診",
        },
    )
    def test_submission_replies_and_clears_state(
        self,
        _get_state,
        post,
        _get_doctor_info,
        _get_bubble,
        clear_state,
    ):
        post.return_value.raise_for_status.return_value = None

        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "公務會議", self.line_bot_api
        )

        self.assertTrue(handled)
        post.assert_called_once()
        self.line_bot_api.reply_message.assert_called_once()
        self.line_bot_api.push_message.assert_not_called()
        clear_state.assert_called_once_with(self.user_id)

    @patch.object(adjust_handler, "clear_state")
    @patch.object(adjust_handler, "get_doctor_info", return_value=("測試醫師", "測試科"))
    @patch.object(adjust_handler.requests, "post", side_effect=RuntimeError("timeout"))
    @patch.object(
        adjust_handler,
        "get_state",
        return_value={
            "step": 2,
            "type": "我要調診",
            "original_date": "10/2 上午診",
            "new_date": "10/3 下午診",
        },
    )
    def test_submission_failure_replies_and_clears_state(
        self, _get_state, _post, _get_doctor_info, clear_state
    ):
        handled = adjust_handler.handle_adjustment(
            self.event, self.user_id, "公務會議", self.line_bot_api
        )

        self.assertTrue(handled)
        reply = self.line_bot_api.reply_message.call_args.args[1]
        self.assertIn("提交失敗", reply.text)
        clear_state.assert_called_once_with(self.user_id)


if __name__ == "__main__":
    unittest.main()
