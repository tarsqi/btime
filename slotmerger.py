from copy import copy

class SlotMerger(type):
    """A metaclass that implements class-slot merging.

    Compound data structures (dict-like or list-like) stored in slots whose
    names are members of the list stored in the __merge__ slot will be
    merged with the values of the same-named slots in each of the class's
    ancestors.  The __merge__ slot is always merged."""

    def __init__(cls, name, bases, dict):
        def inherited_slot_values(slot):
            """Yield the values of slot in each ancestor of cls that supplied
            such a value, from most-distant ancestor to least."""
            for ancestor in reversed(cls.__mro__):
                if ancestor is cls:
                    return
                if slot in ancestor.__dict__:
                    yield ancestor.__dict__[slot]

        def merge_slot_values(slot):
            def merge(old, new):
                """Merge the contents of new into old and return old."""
                if old is None:
                    return copy(new)
                if not (issubclass(type(old), type(new)) or
                        issubclass(type(new), type(old))):
                    raise TypeError("can't merge slots of different types: " +
                                    "%s, %s" % (old, new))
                if hasattr(old, "update"): # e.g., dict
                    old.update(new)
                    return old
                elif hasattr(old, "extend"): # e.g., list
                    old.extend(x for x in new if x not in old)
                    return old
                else:
                    raise RuntimeError("can't merge slot %s.%s" % \
                                           (cls.__name__, slot))
            x = None
            for value in inherited_slot_values(slot):
                x = merge(x, value)
            if slot in dict:
                x = merge(x, dict[slot])
            return x

        super(SlotMerger, cls).__init__(name, bases, dict)
        setattr(cls, "__merge__", merge_slot_values("__merge__"))
        for slot in getattr(cls, "__merge__"):
            setattr(cls, slot, merge_slot_values(slot))

if __name__ == "__main__":
    class A(object):
        __metaclass__ = SlotMerger
        __merge__ = ['foo']
        foo = {'a': 1, 'b': -1}
        bar = ['abc']

    class B(A):
        __merge__ = ['bar']
        foo = {'b': 2}
        bar = ['doe', 're', 'mi']

    class C(A):
        foo = {'c': 3}

    class D(B, C):
        pass

    assert D.foo == {'a': 1, 'b': 2, 'c': 3}
    assert D.bar == ['abc', 'doe', 're', 'mi']
