import unittest
from unittest.mock import Mock, patch

from requests.exceptions import Timeout

from utils import sheet_cache


class SheetCacheTests(unittest.TestCase):
    def setUp(self):
        sheet_cache.clear_sheet_values_cache()

    @patch("utils.sheet_cache.time.sleep")
    @patch("utils.sheet_cache.get_gspread_client")
    def test_retries_transient_failures_inside_one_request(self, get_client, _sleep):
        worksheet = Mock()
        worksheet.get_all_values.side_effect = [
            Timeout("first"),
            Timeout("second"),
            [["id", "name"], ["U1", "Doctor"]],
        ]
        get_client.return_value.open_by_url.return_value.worksheet.return_value = worksheet

        values = sheet_cache.get_sheet_values_by_url("sheet", "UserMapping")

        self.assertEqual(values[1][1], "Doctor")
        self.assertEqual(worksheet.get_all_values.call_count, 3)

    @patch("utils.sheet_cache.get_gspread_client")
    def test_fresh_cache_avoids_a_second_google_call(self, get_client):
        worksheet = Mock()
        worksheet.get_all_values.return_value = [["id"], ["U1"]]
        get_client.return_value.open_by_url.return_value.worksheet.return_value = worksheet

        first = sheet_cache.get_sheet_values_by_url("sheet", "UserMapping")
        second = sheet_cache.get_sheet_values_by_url("sheet", "UserMapping")

        self.assertIs(first, second)
        self.assertEqual(worksheet.get_all_values.call_count, 1)

    @patch("utils.sheet_cache.time.sleep")
    @patch("utils.sheet_cache.get_gspread_client")
    def test_stale_cache_is_used_when_refresh_fails(self, get_client, _sleep):
        worksheet = Mock()
        worksheet.get_all_values.side_effect = [
            [["id"], ["U1"]],
            Timeout("temporary"),
            Timeout("temporary"),
            Timeout("temporary"),
        ]
        get_client.return_value.open_by_url.return_value.worksheet.return_value = worksheet

        expected = sheet_cache.get_sheet_values_by_url("sheet", "UserMapping")
        actual = sheet_cache.get_sheet_values_by_url(
            "sheet", "UserMapping", force_refresh=True
        )

        self.assertIs(actual, expected)


if __name__ == "__main__":
    unittest.main()
