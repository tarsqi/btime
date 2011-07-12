import os
import codecs
import random
import iso8601

from timex import *
from copy import *
#from nltk.classify.naivebayes import *
#from nltk.classify.maxent import *

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
        self.timexes = []
        self.creation_id = None
        sents = [t for t in tml_tokenize(self.text)]
        for i in range(len(sents)):
            self.sentences.append(sents[i])
            for j in range(len(sents[i])):
                token = sents[i][j]
                if isinstance(token, XMLTag):
                    if token.type == 'TIMEX3':
                        self.timexes.append((token.attr_dict['tid'], (i, j)))
                        if token['functionInDocument'] != 'NONE':
                            self.creation_id = token['tid']

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

class Anaphoric(Terminal):
    def __init__(self):
        pass

    def match(self, token):
        return (isinstance(token, TemporalFunction) and \
                not anchor_type(token) == Deictic) or \
               ((isinstance(token, iso8601.TimeRep) or \
                 isinstance(token, iso8601.TimeUnit)) and \
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
        return isinstance(token, TemporalFunction) or \
               isinstance(token, Anchor) or \
               isinstance(token, iso8601.TimeRep) or \
               isinstance(token, iso8601.TimeUnit)

def anchor_type(rep):
    if isinstance(rep, Anchor) or isinstance(rep, iso8601.TimeRep):
        return type(Anchor)
    elif not isinstance(rep, TemporalFunction):
        return None
    else:
        return anchor_type(rep.anchor)

def strip_timexes(doc):
    for k in range(len(doc.sentences)):
        sent = doc.sentences[k]
        for i in range(len(sent)):
            if isinstance(sent[i], XMLTag) and sent[i].type == 'TIMEX3':
                tokens = tokenize(sent[i].text)
                sent = sent[:i] + sent[i+1:]
                for j in range(len(tokens)):
                    sent.insert(i+j, tokens[j])
                doc.sentences[k] = sent

def tag_timexes(doc):
    for i in range(len(doc.sentences)):
        doc.sentences[i] = [p for p in parse(doc.sentences[i])]

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

def write_anaphora(docs=[t for t in get_tml_files()],
                   out_file='anaphoric.txt'):
    anchors = []
    f = codecs.open(out_file, mode='w', encoding='UTF-8')
    for d in docs:
        anchors.extend(write_anaphoric_sents(d, f))
    f.close()
    return anchors

def write_anaphoric_sents(doc, f):
    f.write('File name: %s\n\n' % doc.name)
    anchors = []
    for i in range(len(doc.sentences)):
        for j in range(len(doc.sentences[i])):
            token = doc.sentences[i][j]
            if isinstance(token, XMLTag) and \
               token.type == 'TIMEX3' and \
               token['anchorTimeID'] and \
               token['anchorTimeID'] != doc.creation_id:
                out_list = map(str, doc.sentences[i][:])
                out_list[j] = '<< ' + out_list[j].upper() + ' >>'
                f.write('tid %s sent %d:\n' % (token['tid'], i))
                f.write(' '.join(out_list) + '\n\n')
                anchorID = token['anchorTimeID']
                for t in doc.timexes:
                    if t[0] == anchorID: x, y = t[1]
                out_list = map(str, doc.sentences[x][:])
                out_list[y] = '<< ' + out_list[y].upper() + ' >>'
                f.write('refers to tid %s sent %d:\n' % (anchorID, x))
                tids = map(lambda x: x[0], doc.timexes)
                f.write('%d timexes ago, %d sentences ago.\n' % \
                        (tids.index(token['tid']) - \
                         tids.index(anchorID), i - x))
                f.write(' '.join(out_list) + '\n\n')
                anchors.append(doc.sentences[x][y])
    return anchors

def read_anaphoric_grammar(filename="anaphoric_grammar.txt"):
    with open(filename) as f:
        return parse_grammar_spec(f.readline, "parse", globals())

def anaphoric_parse(tokens):
    return parse(tokens, read_anaphoric_grammar())

file_gen = get_tml_files()
file_gen.next()
file_gen.next()
doc = file_gen.next()

##random.shuffle(all_docs)
##
##training = []
##test = []
##
##for i in range(len(all_docs)):
##    if i < 150:
##        training.extend([f for f in doc_features(all_docs[i], True)
##                         if f[1] != 'UNANCHORED'])
##    else:
##        test.extend([f for f in doc_features(all_docs[i], True)
##                    if f[1] != 'UNANCHORED'])
##
##classifier = MaxentClassifier.train(training, max_iter=10)
##print_stats(test, classifier)
##
