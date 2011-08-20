import os
import codecs
import xml.dom.minidom
import re

from timex import *
from copy import *

tml_dir = 'timebank_1.2/data/timeml'

whitespace_re = re.compile(r'^\s+$')
word_re = re.compile(r'[^\-\s]+[^\'\"\-\.,;:!?\s]')
abbrev_re = re.compile(r'([\.A-Z]+\.)\s[a-z]')
quot_re = re.compile(r'(\'\')|(\')|(``)|(`)|(\")')
sent_end_re = re.compile(r'([\.\?!])\s[A-Z]', re.S)

class TMLFile(object):
    def __init__(self, path):
        self.path = path
        time_ml = xml.dom.minidom.parse(path).childNodes[0]
        self.sents = sentence_tokenize(flatten(map(word_tokenize,
                                                   expand(time_ml))))
        self.timexes = []
        self.creation = None
        is_timex3 = lambda elt: isinstance(elt, xml.dom.minidom.Element) and \
                                elt.nodeName == 'TIMEX3'
        for i in range(len(self.sents)):
            for j in range(len(self.sents[i])):
                token = self.sents[i][j]
                if is_timex3(token): # stopped here
                    timex = TimexTag(token)
                    self.sents[i][j] = timex
                    if timex['functionInDocument'] and \
                       timex['functionInDocument'] != 'NONE':
                        self.creation = timex
                    else:
                        self.timexes.append((timex['tid'], (i, j)))
                                                
    def __str__(self):
        return 'TML File : %s' % self.name

    def __getitem__(self, key):
        """Returns a sentence if key is an int, or a location tuple
           if key is a tid."""
        if isinstance(key, int):
            if key not in range(len(self.sentences)):
                raise KeyError('no such sentence')
            return self.sentences[key]
        elif isinstance(key, basestring) and key[0] == 't':
            for (tid, loc_tup) in self.timexes:
                if key == tid: return loc_tup
            raise KeyError('tid not found')
        raise KeyError('invalid key format')

class XMLTag(object):
    def __init__(self, elt):
        assert isinstance(elt, xml.dom.minidom.Element)
        self.element = elt

    def __str__(self):
        return '<%s %s />' % (self.element.nodeName,
                              self.element.childNodes[0].data or 'None')

    def __getitem__(self, key):
        if self.element.hasAttribute(key):
            return self.element.getAttribute(key)

class TimexTag(XMLTag): pass

class EventTag(XMLTag): pass

class MakeInstanceTag(XMLTag): pass

class Quotation(list):
    def __str__(self):
        return 'Quotation(%s)' % super(Quotation, self).__str__()

    def __repr__(self):
        return 'Quotation(%s)' % super(Quotation, self).__repr__()

def get_timex(doc, tid):
    if tid == doc.creation['tid']:
        return doc.creation
    for timex in doc.timexes:
        if tid == timex[0]:
            x, y = timex[1]
            return doc.sents[x][y]
    return None

def timex_num(doc, num):
    x, y = doc.timexes[num][1]
    return doc.sentences[x][y]

def word_tokenize(elt):
    if not isinstance(elt, basestring): return [elt]
    i = 0
    tokens = []
    while i < len(elt):
        if elt[i] in [' ', '\n']: i += 1
        else:
            matched = False
            for match, gr in zip(map(lambda x: x.match(elt, i),
                                     [quot_re, word_re,
                                      sent_end_re, abbrev_re]),
                                 (0,0,1,1)):
                if match:
                    i += len(match.group(gr))
                    tokens.append(match.group(gr))
                    matched = True
                    break
            if not matched:
                tokens.append(elt[i])
                i += 1
    return tokens

def do_recursive_thing(node, base_case,
                             thing_to_do,
                             dont_do_it=lambda x: False):
    if base_case(node):
        return [thing_to_do(node)]
    out = []
    for child in node.childNodes:
        if dont_do_it(child):
            out.append(child)
        else:
            out.extend(do_recursive_thing(child, base_case,
                                                 thing_to_do,
                                                 dont_do_it))
    return out

def expand(node, leave_elt=lambda elt: elt.nodeName == 'TIMEX3',
                 is_text=lambda elt: elt.nodeName == '#text' and \
                                     not whitespace_re.match(elt.data)):
    return do_recursive_thing(node, is_text, lambda x: x.data, leave_elt)

def flatten(list_of_lists):
    out = []
    for l in list_of_lists:
        if isinstance(l, list):
            out.extend(flatten(l))
        else:
            out.append(l)
    return out

def sentence_tokenize(tokens):
    sents = []
    this_sent = []
    sent_end_punc = ['?', '.', '!']
    sent_end = lambda j: tokens[j] in sent_end_punc and \
                         j > 0 and tokens[j-1] not in sent_end_punc and \
                         j < len(tokens)-1 and \
                         isinstance(tokens[j+1], basestring) and \
                         tokens[j+1].istitle()
    # If two single quotation marks are not tokenized together, or you have
    # an open quotation that never closes, strange things may happen. 
    quot_begin = ['``', '\"']
    quot_end = ['\"', '\'\'']
    i = 0
    while i < len(tokens):
        if tokens[i] in quot_begin:
            if this_sent:
                sents.append(this_sent)
                this_sent = []
            quotation = []
            i += 1
            while i < len(tokens) and not tokens[i] in quot_end:
                quotation.append(tokens[i])
                i += 1
            sents.append(Quotation(quotation))
            i += 1
        else:
            if sent_end(i):
                sents.append(this_sent + [tokens[i]])
                this_sent = []
            else:
                this_sent.append(tokens[i])
            i += 1
    if this_sent: sents.append(this_sent)
    return sents

path = tml_dir + '/AP900815-0044.tml'
time_ml = xml.dom.minidom.parse(path).childNodes[0]
test = expand(time_ml)
sents = sentence_tokenize(flatten(map(word_tokenize, expand(time_ml))))
