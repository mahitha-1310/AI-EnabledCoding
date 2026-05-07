import unittest

class TestAdd(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_negative(self):
        self.assertEqual(add(-1, -1), -2)
    
    def test_false_positive(self):
        self.assertNotEqual(add(1, 1), 3)  # This test is supposed to pass with mistake.
    
    def test_failure(self):
        self.assertEqual(add(2, 2), 5)  # This test is expected to fail.