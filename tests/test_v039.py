import unittest

from folio.v039 import chunk_pages, grid_for_pages, parse_page_range


class V039PrintTests(unittest.TestCase):
    def test_custom_page_range(self):
        self.assertEqual(parse_page_range('1-3, 5, 8-9', 10), [0, 1, 2, 4, 7, 8])

    def test_reversed_range_is_normalized(self):
        self.assertEqual(parse_page_range('5-3', 10), [2, 3, 4])

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            parse_page_range('foo', 10)

    def test_pages_are_grouped_for_n_up_printing(self):
        self.assertEqual(chunk_pages(list(range(7)), 4), [[0, 1, 2, 3], [4, 5, 6]])

    def test_supported_print_grids(self):
        self.assertEqual(grid_for_pages(1), (1, 1))
        self.assertEqual(grid_for_pages(2), (2, 1))
        self.assertEqual(grid_for_pages(4), (2, 2))
        self.assertEqual(grid_for_pages(6), (3, 2))


if __name__ == '__main__':
    unittest.main()
