#!/usr/local/bin/python


import re
from os import listdir
from os.path import isfile, join
import yaml
import string
import utils
from utils import punctuation, brackets


totalWords = {}


def parseFile(filename, d, responses):
  # stores word occurrences for file in the giant word map
  badNames = set()
  prevWords = {} # people to word set
  f = open(filename, 'r')
  for line in f:
    (who, what) = parseLine(line)
    if who != '':
      name = utils.getCanonicalName(who)
      if name is None:
        if who not in ['Topic', 'Mode']:
          badNames.add(who)
      else:
        tokens = utils.tokenizeLine(what)
        storeTokens(name, tokens, d)
        storeResponses(name, set(tokens), prevWords, responses)
        prevWords[name] = set(tokens) # TODO: do more filtering here instead of in storeResponses; move to helper util function
        for word in set(tokens):
          if not word in totalWords:
            totalWords[word] = 0
          totalWords[word] += 1
  print badNames


def storeTokens(who, tokens, d):
  if not who in d:
    d[who] = {}
  pDict = d[who]
  for i in range(len(tokens)-1): # first to second-to-last word
    cword = tokens[i]
    nword = tokens[i+1]
    if not cword in pDict:
      pDict[cword] = {}
    if not nword in pDict[cword]:
      pDict[cword][nword] = 0
    pDict[cword][nword] += 1


def storeResponses(name, tokens, prevWords, responses):
  # responses is person talking to previous person talking to words said previously to word to say to frequency
  if not name in responses:
    responses[name] = {}
  for person in prevWords:
      # if person != name and name != 'diceb0t': # TODO: remove?
      if person not in responses[name]:
        responses[name][person] = {}
      for word in prevWords[person]:
        if all(c in string.letters+'-' for c in word):
          if word not in responses[name][person]:
            responses[name][person][word] = {}
          for cword in tokens:
            if all(c in string.letters+'-' for c in cword):
              if cword not in responses[name][person][word]:
                responses[name][person][word][cword] = 0
              responses[name][person][word][cword] +=1


def parseLine(line):
  # parses line of log, returns the speaker and what they said.
  # returns pair of empty strings if it can't parse.
  # TODO: more flexible toward log types
  # TODO: /me utterances
  m = re.match(r'[0-9]+:[0-9]+ (\S+?): (.*)', line)
  if m:
    who = m.group(1)
    what = m.group(2)
    return (who, what)
  else:
    return ('','')


def filter(frequencies):
  filtered = False
  for person in frequencies:
    badWords = set()
    for cword in frequencies[person]:
      if len(frequencies[person][cword]) <= 1:
        for nword in frequencies[person][cword]: # should be one
          if frequencies[person][cword][nword] <= 1:
            filtered = True
            badWords.add(cword)
    # print badWords, person
    for bw in badWords:
      frequencies[person].pop(bw, None)
    for bw in badWords:
      for cword in frequencies[person]:
        if bw in frequencies[person][cword]:
          frequencies[person][cword].pop(bw, None)
  return filtered


def filterResponses(responses):
  # responses is person talking to previous person talking to words said previously to word to say to frequency
  for name in responses:
    for person in responses[name]:
      emptywords = []
      for word in responses[name][person]:
        if totalWords[word] > 1000:
          emptywords.append(word)
        badwords = []
        for cword in responses[name][person][word]:
          if responses[name][person][word][cword] <= 2 or totalWords[cword] > 1000:
            badwords.append(cword)
        for bw in badwords:
          responses[name][person][word].pop(bw, None)
        if responses[name][person][word] == {}:
          emptywords.append(word)
      for ew in emptywords:
        responses[name][person].pop(ew, None)
        


# main
tokenDict = {} # maps people to words/tokens to next token to frequency
responseDict = {} # maps person talking to previous person talking to words said previously to word to say to frequency
path = '/Users/yanamal/Documents/LimeChat Transcripts/#mage'
logfiles = [ join(path,f) for f in listdir(path) if isfile(join(path,f)) ]
for file in logfiles:
  parseFile(file, tokenDict, responseDict)
filterResponses(responseDict)
print responseDict['fin']['ramc']
'''
while filter(tokenDict):
  pass
'''
# TODO: filters:
# for words with >2 of same letter in a word - shorten to 1? 2? find options in dict?
# convert to lower-case, then deal with punctuation in parsing? record all-caps probability?

# TODO: filter responses:
# filter out most common words overall?
'''
rfile = open('responses.yaml', 'w')
yaml.dump(responseDict, rfile) # TODO: explore manual yaml output for more human-readable file? but then will input have to be manual too?
rfile.close()
'''

'''
freqfile = open('frequencies.yaml', 'w')
yaml.dump(tokenDict, freqfile) # TODO: explore manual yaml output for more human-readable file? but then will input have to be manual too?
freqfile.close()
'''
