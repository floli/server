#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO
# - Change config dir to ~/.config/flofiy/

import codecs
import locale
import argparse, configparser, email, glob, hashlib, os, pickle, re, sys
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from bs4 import BeautifulSoup, UnicodeDammit

def norm_path(*parts):
    """ Returns the normalized, absolute, expanded and joint path, assembled of all parts. """
    parts = [ str(p) for p in parts ] 
    return os.path.abspath(os.path.expanduser(os.path.join(*parts)))

class NormPath(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, norm_path(values))


def parse_args():
    parser = argparse.ArgumentParser(description='Reads an email from stdin, classifies it and outputs to stdout.')
    parser.add_argument("-r", "--rebuild", help="Forget all learned mails and rebuild.",
                        action="store_true")
    parser.add_argument("--config", help="Path to config file.",
                        default = norm_path("~/.flofify/config"), action=NormPath)
    parser.add_argument("--model", help="Model file to use.",
                        default = norm_path("~/.flofify/model"), action=NormPath)
    parser.add_argument("--vocabulary", help="Vocabulary file to use.",
                        default = norm_path("~/.flofify/vocabulary"), action=NormPath)

    return parser.parse_args()

    
class Bucket():
    def __init__(self, name, **args):
        self.name = name
        self.pattern = args["pattern"]
        self.min_probability = float(args["min_probability"])
        
    def __repr__(self):
        return self.name
        
    def files(self):
        fs = glob.glob(self.pattern)
        return fs

    def train_data(self):
        """ Returns a numpy array of shape (n, 3). ID in first row, filenames in second row."""
        files = self.files()
        data = np.array( [[self.name]*len(files), files] )
        return data.transpose()


class Model:
    PICKLE_PROTOCOL = 2

    def __init__(self, buckets):
        self.buckets = buckets

    
    def train(self):
        vectorizer = CountVectorizer(input='filename', decode_error='replace', strip_accents='unicode',
                                     preprocessor=self.mail_preprocessor, stop_words='english')
        transformer = TfidfTransformer()
        self.classifier = MultinomialNB()

        data = np.vstack( [i.train_data() for i in self.buckets] )
        vectors = vectorizer.fit_transform(data[:,1])
        X = transformer.fit_transform(vectors)
        y = data[:,0]
        
        self.classifier.fit(X, y)
        self.vocabulary = vectorizer.vocabulary_
        print("Learned from %s mails, %s buckets." % (data.shape[0], len(self.buckets))) 

    def classify(self, text):
        """ Classsifies text, returns tuple (final class, probability, class). if probability is larger than min_probability then final class == class"""
        vectorizer = CountVectorizer(input="content", vocabulary=self.vocabulary, decode_error='replace', strip_accents='unicode',
                                     preprocessor=self.mail_preprocessor, stop_words='english')
        transformer = TfidfTransformer()
        vectors = vectorizer.transform( [text] )
        X = transformer.fit_transform(vectors)
        proba = np.max(self.classifier.predict_proba(X))
        c = self.classifier.predict(X)[0]
        bucket = next( (b for b in self.buckets if b.name == c) )
        if proba >= bucket.min_probability:
            return (c, proba, c)
        else:
            return (None, proba, c)
        


    def save(self, model_path, vocabulary_path):
        model = open(model_path, "wb")
        pickle.dump(self.classifier, model, self.PICKLE_PROTOCOL)

        voc = open(vocabulary_path, "wb")
        pickle.dump(self.vocabulary, voc, self.PICKLE_PROTOCOL)
        

    def load(self, model_path, vocabulary_path):
        model = open(model_path, "rb")
        self.classifier = pickle.load(model)

        voc = open(vocabulary_path, "rb")
        self.vocabulary = pickle.load(voc)
        
    def mail_preprocessor(self, message):
        # Filter POPFile cruft by matching date string at the beginning.
        pop_reg = re.compile(r"^[0-9]{4}/[0-1][1-9]/[0-3]?[0-9]")
        message = [line for line in message.splitlines(True) if not pop_reg.match(line)]
        msg = email.message_from_string("".join(message))

        msg_body = ""

        for part in msg.walk():
            if part.get_content_type() in ["text/plain", "text/html"]:
                body = part.get_payload(decode=True)
                soup = BeautifulSoup(body)
                msg_body += soup.get_text(" ", strip=True)


        if "-----BEGIN PGP MESSAGE-----" in msg_body:
            msg_body = ""

        msg_body += " ".join(email.utils.parseaddr(msg["From"]))
        try:
            msg_body += " " + msg["Subject"]
        except TypeError: # Can't convert 'NoneType' object to str implicitly
            pass
        msg_body = msg_body.lower()
        return msg_body

        
    
    
class Configuration(configparser.ConfigParser):
    def buckets(self):
        bs = [ Bucket(s, **self[s]) for s in self.sections()]
        return bs

    def __getitem__(self, value):
        """ Needed for python 3 compatibility. """
        return dict(self.items(value))


def log(message):
    print(message, file=logfile)
    

def main():


    args = parse_args()
    config = Configuration()
    config.read(args.config)

    log("Preferred Encoding: " + locale.getpreferredencoding())
    log("LANG: " + os.environ["LANG"])

    model = Model(config.buckets())
    if args.rebuild:
        model.train()
        model.save(args.model, args.vocabulary)
    else:
        # istream = codecs.getreader('utf-8')(sys.stdin)
        # istream = codecs.StreamReader(sys.stdin, errors = "replace")
        # mail = inData.read()
        # mail = sys.stdin.read()
        # sys.stdin = codecs.getreader('utf-8')(sys.stdin.detach())
        # sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        # mail = sys.stdin.read()
        mail = UnicodeDammit(sys.stdin.detach().read())
        log("original_encoding: " + str(mail.original_encoding))
        # mail = open("testmail").read()
        if mail:
            log("Got mail from stdin.")
            model.load(args.model, args.vocabulary)
            classification = model.classify(mail.unicode_markup)
            msg = email.message_from_string(mail.unicode_markup)
            msg["X-Flofify-Class"] = str(classification[0])
            msg["X-Flofify-Probability"] = str(round(classification[1], 4)) + ", " + str(classification[2])
            sys.stdout.write(msg.as_string())
            sys.exit(0)
        else:
            sys.stdout.write(mail.unicode_markup)
            sys.exit(0)


        
logfile = open("flofify.log", "a")

if __name__ == "__main__":
    main()
    
