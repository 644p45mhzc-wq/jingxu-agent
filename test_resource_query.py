import unittest

from backend.resource_search import build_query, has_chinese


class ResourceQueryTests(unittest.TestCase):
    def test_chinese_query_gets_chinese_qualifier(self):
        # Mixing scripts ("数学建模 课程 tutorial") returned nothing from Bing.
        self.assertEqual(build_query('数学建模', 'course'), '数学建模 课程')
        self.assertEqual(build_query('数学建模', 'tutorial'), '数学建模 教程')
        self.assertEqual(build_query('数学建模', 'paper'), '数学建模 论文')

    def test_english_query_gets_english_qualifier(self):
        self.assertEqual(build_query('pandas', 'course'), 'pandas course')
        self.assertEqual(build_query('pandas', 'tutorial'), 'pandas tutorial')
        self.assertEqual(build_query('pandas', 'paper'), 'pandas research paper')

    def test_all_kind_adds_nothing(self):
        self.assertEqual(build_query('数学建模', 'all'), '数学建模')
        self.assertEqual(build_query('pandas', 'all'), 'pandas')

    def test_mixed_query_counts_as_chinese(self):
        self.assertEqual(build_query('Python 数据分析', 'course'), 'Python 数据分析 课程')

    def test_has_chinese(self):
        self.assertTrue(has_chinese('数学'))
        self.assertFalse(has_chinese('pandas'))
        self.assertFalse(has_chinese(''))


if __name__ == '__main__':
    unittest.main()
