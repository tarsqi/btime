
import types, inspect

import timex

from iso8601.iso8601 import TimeUnit, TimeRep, Format


def display(element, indent):

    if type(element) == types.StringType:
        print "%s%s" % (indent, element)

    elif isinstance(element, TimeUnit):
        print "%s%s value=%s" % (indent, type(element), element.value)

    elif isinstance(element, TimeRep):
        value = Format(element.stdformat).format(element) or 'nil'
        print "%s%s value=%s" % (indent, type(element), value)
        for child in element.elements:
            display(child, indent+'   ')

    elif isinstance(element, timex.IncrementOrDecrement):
        print "%s%s" % (indent, type(element))
        print "%s   anchor=%s" % (indent, element.anchor)
        print "%s   unit=%s" % (indent, element.unit)
        
    elif isinstance(element, timex.CoercedTimePoint):
        print "%s%s" % (indent, type(element))
        print "%s   timepoint=%s" % (indent, element.timepoint)
        print "%s   unit=%s" % (indent, element.unit)
        
    elif isinstance(element, timex.TemporalFunction):
        print "%s%s" % (indent, type(element))
        attrs = [a for a in dir(element) if not a.startswith('_')]
        for attr in attrs:
            val = element.__getattribute__(a)
            print "%s   %s = %s" % (indent, attr, val)
        
    else:
        print "WARNING: unknown type", type(t)


#def get_parses(phrases):
#    return [(p, timex.parse(p.split())) for p in phrases]

def print_parses(phrases):
    print
    for p in phrases:
        print p
        result = timex.parse(p.split())
        for t in result:
            display(t, '   ')
        print

def print_parses2(phrases):
    print
    for p in phrases:
        print p
        result = timex.parse2(p.split())
        for t in result:
            print '  ', t[0], type(t[1]), t[1]
        print


if __name__ == '__main__':
    
    phrases = [
        'today',
        'Sunday',
        '29 April',
        'April 29th',
        'April 29th 2000',
        'Sunday , and , the first January 25th',
        #'two weeks',
        #'January 25th 2011',
        #'January 25th , 2011',
        #'Fourth quarter of 2000',
    ]

    print_parses(phrases)
    print_parses2(phrases)


"""

notes:

- printing an instance of TimeRep gives a type error

"""

if __name__ == '__main__':
    
    phrases = [
        'third quarter',
        'third-quarter',
        'third - quarter',
        'Sunday',
        'Sunday morning',
        'October 25',
        'the month',
        'October 25 is the first Sunday of the month',
        ]

    for phrase in phrases:
        print phrase
        result = timex.parse2(phrase.split())
        for x in result:
            print '  ', x[0], type(x[1]), x[1]
