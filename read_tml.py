import os
import codecs

from timex import *
from copy import *

tml_dir = 'timebank_1.2/data/timeml'

# Compiling all these regexes once at the beginning is more efficient.

tag1_re = re.compile(r'<[^>]*>[^<>]+</[^>]*>', re.S)
tag2_re = re.compile(r'<[^<>]+?/>', re.S)
type_re = re.compile(r'<(\S+).*?>', re.S)
text_re = re.compile(r'<[^>]*>(.+?)</[^>]*>', re.S)
whitespace_re = re.compile(r'\s')
word_re = re.compile(r'[^<>\-\s]+[^<>\-\.,;:\s]')
attr_re = re.compile(r'(\S+)=\"(.*?)\"')
sent_end_re = re.compile(r'([\.\?!])\s', re.S)

class TMLFile(object):
    def __init__(self, path, omit_makeins=True):
        self.name = re.search(r'([^/]+?\.tml)', path).group(1)
        f = codecs.open(path, mode='r', encoding='UTF-8')
        self.text = re.sub(r'(\s){2,}', r'\1', 
                           re.search(r'<TimeML.+?>(.*)</TimeML>',
                                     f.read(), re.S).group(1))
        f.close()
        self.sentences = []
        self.timexes = []
        self.creation = None
        sents = [t for t in tml_tokenize(self.text, omit_makeins)]
        for i in range(len(sents)):
            self.sentences.append(sents[i])
            for j in range(len(sents[i])):
                token = sents[i][j]
                if isinstance(token, XMLTag):
                    if token.type == 'TIMEX3':
                        if token['functionInDocument'] and \
                           token['functionInDocument'] != 'NONE':
                            self.creation = token
                        else:
                            self.timexes.append((token.attr_dict['tid'],
                                                 (i, j)))

    def __str__(self):
        return 'TML File : %s' % self.name

    def __getitem__(self, key):
        """Returns a sentence if key is an int, or a timex if key is a tid."""
        if isinstance(key, int):
            return self.sentences[key]
        elif isinstance(key, basestring) and key[0] == 't':
            timex = get_timex(self, key)
            if timex:
                return timex
            else:
                raise KeyError
        raise KeyError

    def reset_timex_indices(self):
        """When you strip out XML tags, the indices in self.timexes get messed
           up. Run this method to reset the indices."""
        self.timexes = []
        for i in range(len(self.sentences)):
            for j in range(len(self.sentences[i])):
                token = self.sentences[i][j]
                if isinstance(token, XMLTag) and token.type == 'TIMEX3' and \
                   token['functionInDocument'] == 'NONE':
                    self.timexes.append((token.attr_dict['tid'], (i, j)))

class XMLTag(object):
    def __init__(self, raw):
        self.raw = raw
        self.type = type_re.search(self.raw).group(1)
        text_match = text_re.search(self.raw)
        self.text = text_match.group(1) if text_match else None
        self.attr_dict = make_attr_dict(self.raw)

    def __str__(self):
        return '<%s> %s' % (self.type, self.text or 'n/a')

    def __getitem__(self, key):
        if self.attr_dict.has_key(key): return self.attr_dict[key]

def get_timex(doc, tid):
    if tid == doc.creation['tid']:
        return doc.creation
    for timex in doc.timexes:
        if tid == timex[0]:
            x, y = timex[1]
            return doc.sentences[x][y]
    return None

def timex_num(doc, num):
    x, y = doc.timexes[num][1]
    return doc.sentences[x][y]

def make_attr_dict(raw_tag):
    i = 0
    attr_dict = {}
    match = attr_re.search(raw_tag, i)
    while match:
        i = match.end()
        attr_dict[match.group(1)] = match.group(2)
        match = attr_re.search(raw_tag, i)
    return attr_dict

def tml_tokenize(raw, omit_makeins=True):
    i = 0
    tokens = []
    while i < len(raw):
        if whitespace_re.match(raw, i):
            i += 1
        else:
            word_match = word_re.match(raw, i)
            if word_match:
                i = word_match.end()
                tokens.append(word_match.group())
            elif raw[i] == '<':
                if omit_makeins and raw[i:].startswith('<MAKEINSTANCE'):
                    break
                for pat in [tag1_re, tag2_re]:
                    tag_match = pat.match(raw, i)
                    if tag_match:
                        i = tag_match.end()
                        tokens.append(XMLTag(tag_match.group()))
            else:
                end_match = sent_end_re.match(raw, i)
                if end_match:
                    i = end_match.end()
                    tokens.append(end_match.group(1))
                    yield tokens
                    tokens = []
                else:
                    tokens.append(raw[i])
                    i += 1
    if len(tokens) > 0:
        yield tokens

def strip_xml(doc_, strip_tag=lambda x: x.type in ['SIGNAL', 'EVENT']):
    doc = deepcopy(doc_)
    for k in range(len(doc.sentences)):
        sent = doc.sentences[k]
        for i in range(len(sent)):
            if isinstance(sent[i], XMLTag) and strip_tag(sent[i]):
                tokens = tokenize(sent[i].text)
                sent = sent[:i] + sent[i+1:]
                for j in range(len(tokens)):
                    sent.insert(i+j, tokens[j])
                doc.sentences[k] = sent
    doc.reset_timex_indices()
    return doc

def tokenize(text):
    """Flattens the output of tml_tokenize (i.e. no sentence tokenization)."""
    sents = [t for t in tml_tokenize(text)]
    toks = []
    for s in sents: toks.extend(s)
    return toks

