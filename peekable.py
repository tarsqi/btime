"""From the Python Cookbook, section 19.18: "Looking Ahead into an Iterator."
By Steven Bethard and Peter Otten; minor tweaks by Alex Plotnick."""

import collections

class peekable(object):
    """An iterator that supports a peek operation. Example usage:
    >>> p = peekable(range(4))
    >>> p.peek()
    0
    >>> p.next(1)
    [0]
    >>> p.peek(3)
    [1, 2, 3]
    >>> p.next(2)
    [1, 2]
    >>> p.peek(2)
    Traceback (most recent call last):
      ...
    StopIteration
    >>> p.peek(1)
    [3]
    >>> p.next(2)
    Traceback (most recent call last):
      ...
    StopIteration
    >>> p.next()
    3
    """

    def __init__(self, iterable):
        self.iterable = iter(iterable)
        self.cache = collections.deque()

    def __iter__(self):
        return self

    def snarf(self, n):
        if n is None:
            n = 1
        while len(self.cache) < n:
            self.cache.append(self.iterable.next())

    def next(self, n=None):
        self.snarf(n)
        if n is None:
            return self.cache.popleft()
        else:
            return [self.cache.popleft() for i in range(n)]

    def peek(self, n=None):
        self.snarf(n)
        if n is None:
            return self.cache[0]
        else:
            return [self.cache[i] for i in range(n)]

if __name__ == "__main__":
    import doctest
    doctest.testmod()
