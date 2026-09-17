import unittest

from folio.v0310 import landscape_for_pages_per_sheet, parse_page_range


class V0310PrintTests(unittest.TestCase):
    def test_empty_custom_range_means_all_pages(self):
        self.assertEqual(parse_page_range('', 5), [0, 1, 2, 3, 4])

    def test_open_ended_range_runs_to_last_page(self):
        self.assertEqual(parse_page_range('5-', 8), [4, 5, 6, 7])

    def test_open_ended_range_can_start_at_first_page(self):
        self.assertEqual(parse_page_range('-3', 8), [0, 1, 2])

    def test_mixed_open_and_closed_ranges(self):
        self.assertEqual(parse_page_range('2, 4-5, 8-', 10), [1, 3, 4, 7, 8, 9])

    def test_two_and_six_up_use_landscape(self):
        self.assertFalse(landscape_for_pages_per_sheet(1))
        self.assertTrue(landscape_for_pages_per_sheet(2))
        self.assertFalse(landscape_for_pages_per_sheet(4))
        self.assertTrue(landscape_for_pages_per_sheet(6))


if __name__ == '__main__':
    unittest.main()
