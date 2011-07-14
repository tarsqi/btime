import os
import codecs
import random
import iso8601

from timex import *
from read_tml import *
from copy import *

class Anaphoric(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return (isinstance(token, TemporalFunction) and \
                not anchor_type(token) == Deictic) or \
               (isinstance(token, (iso8601.TimeRep, iso8601.TimeUnit)) and \
                not isinstance(token, iso8601.CalendarDate))

class Signal(Terminal):
    def __init__(self, word=None):
        self.word = word

    def match(self, token):
        if isinstance(token, XMLTag) and token.type == 'SIGNAL':
            if self.word: return self.word == token.text
            else: return True
        return False

class Timex(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return isinstance(token, (TemporalFunction, Anchor,
                                  iso8601.TimeRep, iso8601.TimeUnit))

def anchor_type(rep):
    if isinstance(rep, Anchor) or isinstance(rep, iso8601.TimeRep):
        return type(Anchor)
    elif not isinstance(rep, TemporalFunction):
        return None
    else:
        return anchor_type(rep.anchor)

def strip_timexes(doc_):
    doc = deepcopy(doc_)
    for k in range(len(doc.sentences)):
        sent = doc.sentences[k]
        for i in range(len(sent)):
            if isinstance(sent[i], XMLTag) and sent[i].type == 'TIMEX3':
                tokens = tokenize(sent[i].text)
                sent = sent[:i] + sent[i+1:]
                for j in range(len(tokens)):
                    sent.insert(i+j, tokens[j])
                doc.sentences[k] = sent
    return doc

def tag_timexes(doc_, verbose=False):
    doc = deepcopy(doc_)
    for i in range(len(doc.sentences)):
        sent = []
        for p in parse(doc.sentences[i]):
            if verbose and not isinstance(p, (basestring, XMLTag)):
                print 'parsed %s' % p
            sent.append(p)
        doc.sentences[i] = sent
    return doc
        
def get_tml_files(directory=tml_dir):
    for f in os.listdir(tml_dir):
        if f.endswith('.tml'):
            yield TMLFile(tml_dir + '/' + f)

def doc_features(doc, add_labels=True, timex_window=[-3,-2,-1,1],
                                       token_window=[-1,1]):
    feature_sets = []
    for i in range(len(doc.timexes)):
        x, y = doc.timexes[i][1]
        timex = doc.sentences[x][y]
        features = token_features(timex)
        for j in token_window:
            if y+j > 0 and y+j < len(doc.sentences[x]):
                 features.update(prefixed_dict(
                                 token_features(doc.sentences[x][y+j]),
                                 'token_%d' % j))
        for j in timex_window:
            if i+j > 0 and i+j < len(doc.timexes):
                 features.update(prefixed_dict(
                                 token_features(get_timex(doc, i+j)),
                                 'timex_%d' % j))
        if add_labels:
            if not timex['anchorTimeID']:
                label = 'UNANCHORED'
            elif timex['anchorTimeID'] == doc.creation_id:
                label = 'DEICTIC'
            else:
                tids = map(lambda x: x[0], doc.timexes)
                label = tids.index(timex['tid']) - \
                        tids.index(timex['anchorTimeID'])
            features = (features, label)
        feature_sets.append(features)
    return feature_sets

def get_timex(doc, tid):
    for timex in doc.timexes:
        if tid == timex[0]:
            x, y = timex[1]
            return doc.sentences[x][y]
    return None

def token_features(token):
    features = {}
    if isinstance(token, XMLTag):
        if token.type == 'TIMEX3':
            try:
                pgen = parse(tokenize(token.text))
                timex_objects = [p for p in pgen]
                features['type'] = type(timex_objects[-1]).__name__
            except Exception:
                features['type'] = 'n/a'
        else:
            features['type'] = token.type
            features['text'] = token.text
    else:
        features['text'] = token
    return features

def prefixed_dict(dictionary, prefix):
    out = {}
    for key in dictionary:
        out['%s_%s' % (prefix, key)] = dictionary[key]
    return out

def read_anaphoric_grammar(filename="anaphoric_grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "parse", globals())
    
def anaphoric_parse(tokens):
    return parse(tokens, read_anaphoric_grammar())

