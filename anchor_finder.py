import os
import codecs
import random
import iso8601

from timex import *
from read_tml import *

class NotATimexError(Exception): pass

# Don't get confused - these are TERMINALS for the anchor grammar.

class Anaphoric(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return (isinstance(token, TemporalFunction) and \
                not anchor_type(token) == Deictic) or \
               (isinstance(token, (iso8601.TimeRep, iso8601.TimeUnit)) and \
                not isinstance(token, (iso8601.CalendarDate, iso8601.Year)))

class Timex(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return isinstance(token, (TemporalFunction, iso8601.TimeRep,
                                  iso8601.TimeUnit))

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

def doc_features(doc_, add_labels=True, timex_window=range(-8,2),
                                        token_window=[-1,1],
                                        anchored_classifier=None):
    doc = strip_xml(doc_)
    pair_features = []
    timex_features = []
    timexes = []
    if anchored_classifier:
        anchored_feat = anchored_features(doc, False)
    for i in range(len(doc.timexes)):
        if not (anchored_classifier and \
                anchored_classifier.classify(anchored_feat[i]) == 'UNANCHORED'):
            x, y = doc.timexes[i][1]
            timex = doc.sentences[x][y]
            timexes.append(timex)
            these_features = token_features(timex)
            for j in token_window:
                if y+j >= 0 and y+j < len(doc.sentences[x]):
                     these_features.update(prefixed_dict(
                                           token_features(doc.sentences[x][y+j]),
                                           'token_%d' % j))
            timex_features.append(these_features)
    for i in range(len(timex_features)):
        for j in timex_window:
            pair = {}
            if i+j >= 0 and i+j < len(timexes) and j != 0:
                pair = pairwise_features(timex_features[i],
                                         timex_features[i+j],
                                         j)
                if add_labels:
                    if anchored(timexes[i]) and \
                       anchored(timexes[i]) == timexes[i+j]['tid']:
                        label = anchoring_type(timexes[i])
                    else: label = 'NOT_AN_ANCHOR'
                    if len(pair) > 0:
                        pair = (pair, label)
            if len(pair) > 0: pair_features.append(pair)
    return pair_features

def anchored_features(doc_, add_labels=True, token_window=[-1,1]):
    doc = strip_xml(doc_)
    feature_sets = []
    for i in range(len(doc.timexes)):
        x, y = doc.timexes[i][1]
        timex = doc.sentences[x][y]
        features = token_features(timex)
        for j in token_window:
            if y+j >= 0 and y+j < len(doc.sentences[x]):
                 features.update(prefixed_dict(
                                 token_features(doc.sentences[x][y+j]),
                                 'token_%d' % j))
        if add_labels:
            if anchored(timex):
                label = 'ANCHORED'
            else:
                label = 'UNANCHORED'
            features = (features, label)
        feature_sets.append(features)
    return feature_sets

def pairwise_features(timex1_features, timex2_features, distance):
    pairwise = {}
    pairwise.update(timex1_features)
    pairwise.update(prefixed_dict(timex2_features, 'other'))
    if distance > 0:
        if distance < 3:
            pairwise['distance'] = 'NEAR'
        elif distance < 5:
            pairwise['distance'] = 'MEDIUM'
        else:
            pairwise['distance'] = 'FAR'
    else:
        pairwise['distance'] = 'AHEAD'
    pairwise['scale'] = greater_scale(timex1_features['timex_type'],
                                      timex2_features['timex_type'])
    return pairwise

def corpus_features(corpus, feature_func=doc_features, restrictor=None):
    feature_sets = []
    for doc in corpus:
        if not restrictor:
            feature_sets.extend(feature_func(doc))
        else:
            feature_sets.extend(feature_func(doc, anchored_classifier=restrictor))
    return feature_sets

begin_words = ['beginning', 'starting']
end_words = ['ending']
after_words = ['after', 'later', 'following']
before_words = ['before', 'earlier', 'prior']

definite_this = ['the', 'this', 'these']
definite_that = ['that', 'those']
indefinite = ['a', 'an', 'some', 'several']

def token_features(token):
    features = {}
    if isinstance(token, XMLTag):
        if token.type == 'TIMEX3':
            tokens = tokenize(token.text)
            if isinstance(tokens[0], basestring):
                if tokens[0].lower() in definite_this:
                    features['def_this'] = True
                elif tokens[0].lower() in definite_that:
                    features['def_that'] = True
                elif tokens[0].lower() in indefinite:
                    features['indef'] = True
            pgen = parse(tokens)
            try:
                timex_objects = [p for p in pgen]
                features['timex_type'] = timex_type(timex_objects[-1]).__name__
                type_of_anchor = anchor_type(timex_objects[-1])
                if type_of_anchor:
                    features['anchor_type'] = type_of_anchor.__name__
                else:
                    features['anchor_type'] = None
            except TypeError:
                features['timex_type'] = 'UNKNOWN'
    else:
        token = token.lower()
        if token in begin_words: features['begin_word'] = True
        elif token in end_words: features['end_word'] = True
        elif token in after_words: features['after_word'] = True
        elif token in before_words: features['before_word'] = True
        elif token == 'of': features['of'] = True
        elif token == 'for': features['for'] = True
    return features

scale = [['CalendarDate', 'Year'],
         ['Quarter'],
         ['MonthDate', 'Month'],
         ['DayOfWeek', 'DateTime']]

def greater_scale(name1, name2):
    scale1 = None
    scale2 = None
    for i in range(len(scale)):
        if name1 in scale[i]: scale1 = i
        if name2 in scale[i]: scale2 = i
    if not (scale1 and scale2) or scale1 == scale2: return 0
    elif scale1 > scale2: return 1
    elif scale2 > scale1: return -1

def prefixed_dict(dictionary, prefix):
    out = {}
    for key in dictionary:
        out['%s_%s' % (prefix, key)] = dictionary[key]
    return out
