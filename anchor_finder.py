import os
import codecs
import random
import iso8601

from timex import *
from read_tml import *
from copy import *

# Don't get confused - these are TERMINALS for the anaphoric grammar.

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
        self.word = word.lower()

    def match(self, token):
        if isinstance(token, XMLTag) and token.type == 'SIGNAL':
            if self.word: return self.word == token.text.lower()
            else: return True
        return False

class Timex(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return isinstance(token, (TemporalFunction, Anchor,
                                  iso8601.TimeRep, iso8601.TimeUnit))

class HybridClassifier(object):
    def __init__(self, anchor_classifier, anchored_classifier,
                       anchor_features=anchor_features,
                       anchored_features=anchored_features):
        self.anchor_classifier = anchor_classifier
        self.anchored_classifier = anchored_classifier
        self.anchor_features = anchor_features
        self.anchored_features = anchored_features

    def classify(doc):
        tids = [x[0] for x in doc.timexes]

def anchor_type(timex):
    if isinstance(timex, Anchor): return type(timex)
    elif isinstance(timex, TemporalModifier): return anchor_type(timex.timex)
    elif isinstance(timex, TemporalFunction):
        try:
            return anchor_type(timex.anchor)
        except AttributeError:
            pass

def timex_type(timex):
    if isinstance(timex, TemporalModifier): return timex_type(timex.timex)
    elif isinstance(timex, TemporalFunction): return type(timex)

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

def anchored_features(doc, add_labels=True, timex_window=[-4,-3,-2,-1,1,2],
                                            token_window=[-2,-1,1,2]):
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
                                 token_features(timex_num(doc, i+j)),
                                 'timex_%d' % j))
        if add_labels:
            if not anchored(timex):
                label = 'UNANCHORED'
            elif anchored(timex) == doc.creation_id:
                label = 'CREATION'
            else:
                label = 'REF_TIME'
            features = (features, label)
        feature_sets.append(features)
    return feature_sets

def anchor_features(doc, add_labels=True, timex_window=[-3,-2,-1,1],
                                          token_window=[-1,1]):
    feature_sets = []
    if add_labels:
        anchors = set()
        for i in range(len(doc.timexes)):
            x, y = doc.timexes[i][1]
            timex = doc.sentences[x][y]
            if anchored(timex): anchors.add(anchored(timex))
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
                                 token_features(timex_num(doc, i+j)),
                                 'timex_%d' % j))
        if add_labels:
            if timex['tid'] in anchors:
                label = 'ANCHOR'
            else:
                label = 'NOT_AN_ANCHOR'
            features = (features, label)
        feature_sets.append(features)
    return feature_sets

def anchored(timex):
    return timex['anchorTimeID'] or timex['beginPoint'] or timex['endPoint']

def get_timex(doc, tid):
    for timex in doc.timexes:
        if tid == timex[0]:
            x, y = timex[1]
            return doc.sentences[x][y]
    return None

def timex_num(doc, num):
    x, y = doc.timexes[num][1]
    return doc.sentences[x][y]

def token_features(token):
    features = {}
    if isinstance(token, XMLTag):
        if token.type == 'TIMEX3':
            try:
                tokens = tokenize(token.text)
                features['last_token'] = (re.sub(r'\d', '#',
                                                 tokens[-1])).lower()
                pgen = parse(tokens)
                timex_objects = [p for p in pgen]
                features['timex_type'] = timex_type(timex_objects[-1]).__name__
                features['anchor_type'] = anchor_type(timex_objects[-1]).__name__
            except Exception:
                features['timex_type'] = 'TIMEX'
        elif token.type == 'SIGNAL':
            features['signal'] = True
            features['signal_text'] = token.text
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

