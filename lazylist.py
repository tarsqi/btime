"""A simple implementation of a lazy sequence."""

import itertools

class LazyList(object):
    """A random-access sequence that pulls items from an underlying iterable as
    necessary."""

    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.data = []

    def __getitem__(self, i):
        def snarf(i):
            while i is None or i >= len(self.data):
                self.data.append(self.iterator.next())

        if isinstance(i, int):
            if i < 0:
                raise IndexError("negative indexes are not supported")
            snarf(i)
            return self.data[i]
        elif isinstance(i, slice):
            if any(x is not None and x < 0 for x in (i.start, i.stop)):
                raise IndexError("negative indexes are not supported")
            try:
                snarf(max((i.start, i.stop-1 if i.stop is not None else None)))
            except StopIteration:
                # Slice indices are silently truncated to fall in the
                # allowed range.
                pass
            return self.data[i]
        else:
            raise TypeError("index must be an integer or a slice")

    def __iter__(self):
        return itertools.chain(self.data, self.iterator)
