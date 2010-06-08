import unittest

from lazylist import LazyList

class RecordingIterator(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.log = []

    def __iter__(self):
        return self

    def next(self):
        next = self.iterator.next()
        self.log.append(next)
        return next

class LazyListTest(unittest.TestCase):
    def test_integer_index(self):
        i = RecordingIterator(range(5))
        ll = LazyList(i)
        self.assertEqual(ll[0], 0)
        self.assertEqual(ll[1], 1)
        self.assertEqual(i.log, [0, 1])

    def test_slice(self):
        i = RecordingIterator(range(5))
        ll = LazyList(i)
        self.assertEqual(ll[0:3:2], [0, 2])
        self.assertEqual(i.log, [0, 1, 2])

    def test_negative_index(self):
        ll = LazyList(range(5))
        self.assertRaises(IndexError, lambda: ll[-1])
        self.assertRaises(IndexError, lambda: ll[-1:1])
        self.assertRaises(IndexError, lambda: ll[1:-1])

if __name__ == "__main__":
    try:
        unittest.main()
    except SystemExit:
        pass
