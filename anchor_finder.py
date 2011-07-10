import os
import codecs

from timex import *
from nltk.classify.naivebayes import *
from nltk.classify.maxent import *

tml_dir = 'timebank_1.2/data/timeml'

# Compiling all these regexes once at the beginning is more efficient.

tag1_re = re.compile(r'<[^>]*>[^<>]+</[^>]*>', re.S)
tag2_re = re.compile(r'<[^<>]+?/>', re.S)
type_re = re.compile(r'<(\S+).*?>', re.S)
text_re = re.compile(r'<[^>]*>(.+?)</[^>]*>', re.S)
whitespace_re = re.compile(r'\s')
word_re = re.compile(r'[^<>\s]+[^<>\.,;:\s]')
attr_re = re.compile(r'(\S+)=\"(.*?)\"')
sent_end_re = re.compile(r'([\.\?!])\s', re.S)

class TMLFile(object):
    def __init__(self, path):
        self.name = re.search(r'([^/]+?\.tml)', path).group(1)
        f = codecs.open(path, mode='r', encoding='UTF-8')
        self.text = re.sub(r'(\s){2,}', r'\1', 
                           re.search(r'<TimeML.+?>(.*)</TimeML>',
                                     f.read(), re.S).group(1))
        f.close()
        self.sentences = []
        self.timex_dict = {}
        self.makeinstance_dict = {}
        self.creation_id = None
        for s in tml_tokenize(self.text):
            self.sentences.append(s)
            for t in s:
                if isinstance(t, XMLTag):
                    if t.type == 'TIMEX3':
                        self.timex_dict[t.attr_dict['tid']] = t
                        if t['functionInDocument'] != 'NONE':
                            self.creation_id = t['tid']
                    elif t.type == 'MAKEINSTANCE':
                        self.makeinstance_dict[t.attr_dict['eventID']] = t

    def __str__(self):
        return 'TML File : %s' % self.name

    def __getitem__(self, key):
        return self.sentences[key]

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

def tml_tokenize(raw):
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

def make_attr_dict(raw_tag):
    i = 0
    attr_dict = {}
    match = attr_re.search(raw_tag, i)
    while match:
        i = match.end()
        attr_dict[match.group(1)] = match.group(2)
        match = attr_re.search(raw_tag, i)
    return attr_dict
        
def get_tml_files(directory=tml_dir):
    for f in os.listdir(tml_dir):
        if f.endswith('.tml'):
            yield TMLFile(tml_dir + '/' + f)

def doc_features(doc, add_labels=False):
    feature_sets = []
    for sent in doc.sentences:
        feature_sets.extend(sent_features(sent, doc, add_labels))
    return feature_sets

def timex_features(element):
    features = {}
    if element.attr_dict.has_key('value'):
        features['value'] = re.sub('\d', '#', element['value'])
    if element.attr_dict.has_key('temporalFunction'):
        features['temporalFunction'] = element['temporalFunction']
    if element.attr_dict.has_key('type'):
        features['type'] = element['type']
    tokens = element.text.split(' ')
    features['first_token'] = tokens[0]
    features['last_token'] = tokens[-1]
    if len(tokens) > 1:
        features['last_-1_token'] = tokens[-2]
    return features

def sent_features(sent, doc, add_labels=True):
    timexes = [token for token in sent 
               if isinstance(token, XMLTag) and token.type == 'TIMEX3']
    if len(timexes) == 0:
        return []
    out = []
    event_feature_dict = {}
    event_attrs = ['polarity', 'pos', 'tense', 'aspect']
    events = [event_features(token, doc) for token in sent 
              if isinstance(token, XMLTag) and token.type == 'EVENT']
    for event in events:
        for attr in event_attrs:
            event_feature_dict['there_is_event_' + attr] = event[attr]
    for timex in timexes:
        features = timex_features(timex)
        features.update(event_feature_dict)
        if add_labels:
            if not timex['anchorTimeID']:
                label = 'UNANCHORED'
            elif timex['anchorTimeID'] == doc.creation_id:
                label = 'DEICTIC'
            else:
                label = 'ANAPHORIC'
            features = (features, label)
        out.append(features)
    return out

def event_features(event, doc):
    features = doc.makeinstance_dict[event['eid']].attr_dict.copy()
    for attr in ['eventID', 'eiid']: features.pop(attr)
    return features

def print_stats(test_feature_sets, classifier):
    "Displays statistics for the given classifier."
    for tag in sorted(set(x[1] for x in test_feature_sets)):
        print 'TAG:', tag
        print_label_stats(test_feature_sets, classifier, tag)

def print_label_stats(test_feature_sets, classifier, target_label):
    "Prints precision, recall and F-measure for the target label."
    gold = []
    classified = []
    for i in range(len(test_feature_sets)):
        (features, label) = test_feature_sets[i]
        if label == target_label:
            gold.append(i)
        if classifier.classify(features) == target_label:
            classified.append(i)
    try:
        print 'Precision: %.2f' % nltk.metrics.precision(set(gold),
                                                         set(classified))
        print 'Recall: %.2f' % nltk.metrics.recall(set(gold),
                                                   set(classified))
        print 'F-measure: %.2f' % nltk.metrics.f_measure(set(gold),
                                                         set(classified))
    except Exception:
        print 'n/a'

all_docs = [t for t in get_tml_files()]
training = []
test = []

for i in range(len(all_docs)):
    if i < 150:
        training.extend(doc_features(all_docs[i], True))
    else:
        test.extend(doc_features(all_docs[i], True))

classifier = MaxentClassifier.train(training, max_iter=20)
print_stats(test, classifier)
