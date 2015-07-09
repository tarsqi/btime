import timex

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
