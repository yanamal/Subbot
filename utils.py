import re

punctuation = '\.\,\?\!'
brackets = '\(\)\[\]\<\>\"\"' # TODO: hierarichical decomposition and composition


# TODO: store people information in file, read/write
# also if no file, generate flat file.

# semi-canonical starts of people's names
people = ['yana', 'fin', 'merle', 'ramc', 'kurr', 'kes', 'pere', 'diceb0t', 'tele']

# aliases (mostly IC - but there are lots of outliers for ooc chatter with ic names and vice versa)
aliases = {'candace': 'merle',
           'leigh': 'pere',
           'rudy': 'kurr',
           'docjones': 'kurr',
           'prelate': 'kes',
           'prelatus': 'kes',
           'drjones': 'kurr',
           'doc-rdj': 'kurr',
           'docrdj': 'kurr',
           'doceon': 'fin',
           'ken': 'fin'}


def getCanonicalName(who):
  who = who.lower()
  who = who.strip('_')
  if who == '':
    return
  if who in aliases:
    return aliases[who]
  for person in people:
    if who.startswith(person):
      return person
  return


def tokenizeLine(what):
  tokens = ['\\s'] # start with start-of-sentence token
  # separate by punctuation and brackets
  separators = punctuation+brackets
  what = re.sub(r'https?://\S*', '#link#', what)
  chunks = re.split('(['+separators+'\s])', what)
  for chunk in chunks:
    chunk = chunk.strip()
    if chunk != '' and (chunk not in brackets): # TODO: stop filtering out brackets, start hierarchy logic
      tokens.append(chunk)
  tokens.append('\\e') # end-of-sentence token
  return tokens

