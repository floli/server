#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse, configparser, email, glob, os, pickle, re, sys
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from bs4 import BeautifulSoup, UnicodeDammit

import common
from common import XDG_CONFIG_HOME, XDG_DATA_HOME


class NormPath(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, common.norm_path(values))


def parse_args():
    parser = argparse.ArgumentParser(description='Reads an email from stdin, classifies it and outputs to stdout.')
    parser.add_argument("-r", "--rebuild", help="Forget all learned mails and rebuild.",
                        action="store_true")
    parser.add_argument("--config", help="Path to config file.",
                        default = XDG_CONFIG_HOME("flofify", "config"), action=NormPath)
    parser.add_argument("--model", help="Model file to use.",
                        default = XDG_DATA_HOME("flofify", "model"), action=NormPath)
    parser.add_argument("--vocabulary", help="Vocabulary file to use.",
                        default = XDG_DATA_HOME("flofify", "vocabulary"), action=NormPath)

    return parser.parse_args()

    
class Bucket():
    def __init__(self, name, **args):
        self.name = name
        self.patterns = args["patterns"]
        self.min_probability = float(args["min_probability"])
        
    def __repr__(self):
        return self.name

    def files(self):
        fs = []
        for pattern in self.patterns.split(":"):
            fs += glob.glob(pattern)
        return fs

    def train_data(self):
        """ Returns a numpy array of shape (n, 3). ID in first row, filenames in second row."""
        files = self.files()
        data = np.array( [[self.name]*len(files), files] )
        return data.transpose()


class Model:
    PICKLE_PROTOCOL = 2

    def __init__(self, buckets, fields):
        self.buckets = buckets
        self.fields = fields

    
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
        print("Learned from %s mails." % data.shape[0])
        print("Buckets: %s" % self.buckets)
        print("Fields:  %s" % self.fields)

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
        """ Extracts the text. Combines body, From and Subject headers."""
        # Filter POPFile cruft by matching date string at the beginning.
        pop_reg = re.compile(r"^[0-9]{4}/[0-1][1-9]/[0-3]?[0-9]")
        message = [line for line in message.splitlines(True) if not pop_reg.match(line)]
        msg = email.message_from_string("".join(message))
        
        msg_body = ""

        if "body" in self.fields:
            for part in msg.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    body = part.get_payload(decode=True)
                    soup = BeautifulSoup(body)
                    msg_body += soup.get_text(" ", strip=True)

            """ Ignore encrypted messages. """
            if "-----BEGIN PGP MESSAGE-----" in msg_body:
                msg_body = ""
                
        if "from" in self.fields:
            msg_body += " ".join(email.utils.parseaddr(msg["From"]))

        if "subject" in self.fields:
            try:
                msg_body += " " + msg["Subject"]
            except TypeError: # Can't convert 'NoneType' object to str implicitly
                pass
                
        msg_body = msg_body.lower()
        return msg_body

        
    
    
class Configuration(configparser.ConfigParser):
    def buckets(self):
        """ Returns a list of every config section that starts with "Bucket:", with the leading "Bucket:" cut out from the buckets name."""
        bs = [ Bucket(s[7:], **self[s]) for s in self.sections() if s.startswith("Bucket:") ]
        return bs

    def default_bucket(self):
        return self["Global"].get("default_bucket", "None")

    def fields(self):
        default_fields = "From Subject Body"    
        f = self["Global"].get("fields", default_fields)
        f = f.lower()
        return [ i.strip() for i in f.split(" ") ]

def main():
    args = parse_args()

    common.mkpath(os.path.split(args.config)[0])
    common.mkpath(os.path.split(args.model)[0])
    common.mkpath(os.path.split(args.vocabulary)[0])
    
    config = Configuration()
    config.read(args.config)

    model = Model(config.buckets(), config.fields())
    if args.rebuild:
        model.train()
        model.save(args.model, args.vocabulary)
    else:
        mail = UnicodeDammit(sys.stdin.detach().read())
        if mail:
            model.load(args.model, args.vocabulary)
            classification = model.classify(mail.unicode_markup)
            msg = email.message_from_string(mail.unicode_markup)
            if classification[0] == None:
                msg["X-Flofify-Class"] = config.default_bucket()
            else:
                msg["X-Flofify-Class"] = str(classification[0])
            
            msg["X-Flofify-Probability"] = str(round(classification[1], 4)) + ", " + str(classification[2])
            sys.stdout.write(msg.as_string())
        else:
            sys.stdout.write(mail.unicode_markup)




if __name__ == "__main__":
    main()
