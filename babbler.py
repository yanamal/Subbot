#!/usr/local/bin/python


from random import randrange
import yaml
import ssl
import socket
import sys
import re
import utils
from utils import punctuation, brackets
import math



#### Markov chain stuff


# Data for markov chain generation. Loaded from file and then stays constant.
frequencies = {}
responses = {}


prevWords = {} # previous utterance for each person talking. Persists across function calls, but mutates.


def generateString(frequencies, modifier = None):
  # assumes dict of words to
  #   dict of next-words to num. of occurrences
  # and special '\\s' and '\\e' words to signify start/end of utterance
  # modifier is a dictionary of extra scores for special words
  cword = '\\s'
  nword = ''
  string = ''
  while nword != '\\e':
    # figure out next word
    # TODO: preprocess sum/vals too?
    f = frequencies[cword]
    sum = 0
    vals = []
    for word in f:
      sum += f[word]
      if modifier and word in modifier:
        sum += modifier[word]
      vals.append((sum, word))
    if sum > 0:
      select = randrange(sum)
      for val in vals: # TODO: binary search
        if val[0] > select:
          nword = val[1]
          break
    else:
      print "sum was 0 for cword="+cword+"nword="+nword+"f="+str(f) # TODO: why does this happen?
      return string
    
    # append word/token, figure out spaces
    # TODO: spacing for bracket types
    if nword == '\\e':
      continue  # break also works - last time through anyways
    if nword not in punctuation:
      string += ' '
    if nword == '#link#':
      string += 'http://i.imgur.com/Jkq8ywe.png'
    else:
      string += nword
    cword = nword
    
  return string

def babble(who, freqs, mod=None):
  return generateString(freqs[who], mod)


def initializeData():
  global frequencies, responses
  print "loading frequencies data..."
  freqfile = open('frequencies.yaml', 'r')
  frequencies = yaml.load(freqfile)
  print "loading responses data..."
  rfile = open('responses.yaml', 'r')
  responses = yaml.load(rfile)
  print responses['fin']['yana']



#### Bot stuff



### IRC stuff


server = "irc.arcti.ca"
port = 6697
password = ""
channel = "#Mage"
botnick = "Subb0t"
irc_C = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #defines the socket
irc = ssl.wrap_socket(irc_C)


def tryGettingInput(callback):
  # try reading a line of IRC input.
  # callback is a function that takes one argument - the raw line of input - and processes it as desired.
  try:
    text=irc.recv(2040) # wait for the next bit of input from the IRC server. Limit to 2040 characters.
    # (the rest would stay in the buffer and get processed afterwards, I think)
    if text.strip() != '':
      print text
    # Prevent Timeout - this is how the IRC servers know to kick you off for inactivity, when your client doesn't PONG to a PING.
    if text.find('PING') != -1: # if there is a "PING" anywhere in the text
      sendIrcCommand('PONG ' + text.split()[1] + '\r\n')
      # TODO: what's with the 'PONG AUTH' when first connecting connecting? debug.
    return callback(text) # actually process the input
  except Exception as e:
    # this prints the error message whenever something throws an exception.
    (exType, value, traceback) = sys.exc_info()
    print str(e)
    print 'on line '+str(traceback.tb_lineno) # TODO: why does it get the second to last line number?
    sendMsg('Oops, I derped') # TODO(yanamal): user preference for "PM me error messages"?
    sendMsg(str(e))
    


def respondToConnectionCommands(text):
  # see if the text contains commands for the bot to respond to in order to complete the connection
  # respond as necessary.
  # look for PONG requestes and welcome messages of the format:
  # ":irc.eversible.com 001 yanabot :Welcome to the EFNet Internet Relay Chat Network yanabot""
  connected = False
  if text.find('To connect type /QUOTE PONG') != -1:
    sendIrcCommand('PONG' + text.split('To connect type /QUOTE PONG')[1] + '\r\n')
  
  if text.find('Welcome') != -1: # Note: for some reason the match fails on the 'EFNet' part of the expected welcome message.
    # leaving it at just 'Welcome'. Nothing can go wrong.
    sendIrcCommand("PRIVMSG nickserv :iNOOPE\r\n") #auth
    sendIrcCommand("JOIN "+ channel +"\n")
    connected = True
  return connected


def connectAndJoin():
  # connect to irc, then join the channel requested.
  
  print "Establishing connection to [%s]" % (server)
  # Connect
  irc.connect((server, port))
  sendIrcCommand("USER "+ botnick +" "+ botnick +" "+ botnick +" :testbot\n")
  sendIrcCommand("NICK "+ botnick +"\n")
  
  connected = False
  while not connected:
    connected = tryGettingInput(respondToConnectionCommands)


def inputLoop():
  # An infinite loop waiting for input and processing it.
  while True:
    tryGettingInput(processInput)


def sendIrcCommand(command):
  # send IRC command and also print it to the console
  # TODO: get rid of \n in calls to sendIrcCommand
  irc.send(command+'\n')
  print ' > '+command


### Actual Bot Logic

beingWho = None

def processInput(text):
  # process a line of text from the IRC server.
  global channel, frequencies, beingWho, avgQuality
  # try to get contents of a message
  # these functions will return emtpy things if it wasn't actually a message to the channel
  firstAndRest = getFirstWordAndRest(text)
  userName = getName(text)
  
  # initialize helper variables for responding to message:
  (chan, message) = getMsg(text)
  firstWord = ""
  restOfText = ""
  allWords = message.split()
  
  if len(firstAndRest) > 0:  # must have found a message to the channel
    firstWord = firstAndRest[0]
    if len(firstAndRest) > 1: # there is more than one word in the message
      restOfText = firstAndRest[1].strip()
  
  # respond to message as needed:
  
  if firstWord == 'hay':
    sendMsg(userName+', hay v:', chan)
  if message.startswith('Subbot, be '):
    who = allWords[2]
    person = utils.getCanonicalName(who)
    if person in frequencies:
      sendIrcCommand('nick _'+person+'_\n')
      sendMsg(babble(person, frequencies))
      beingWho = person
      avgQuality = 5
    else:
      sendMsg("who's "+who+"?")
  if message.strip() == 'Subbot, stop':
    sendIrcCommand('nick '+botnick+'\n')
    beingWho = None
  # tell me what is in your database!
  m = re.match(r'if (.+?) says (.+?), what does (.+?) say?', message)
  if m:
    print "getting responses"
    person = m.group(1)
    word = m.group(2)
    me = m.group(3)
    print me, person, word
    if (me in responses) and (person in responses[me]) and (word in responses[me][person]):
      sendMsg(str(responses[me][person][word]), chan)
    else:
      sendMsg("no data!", chan)
  ''' 
  # testing code. TODO: flag?
  m = re.match(r'[0-9]+:[0-9]+ (\S+?): (.*)', message)
  if m:
    maybeRespond(m.group(1), m.group(2))
  '''

## Message sending


def sendMsg(line, chan=None):
  # send message to irc channel
  if not chan:
    chan = channel
  maxlen = 420 # max. length of message to send. Approximately size where it cuts off 
  # (428 in tests, but I suspect it depends on the prefixes like "PRIVMSG ..." etc.)
  explicit_lines = line.split('\n')
  for el in explicit_lines:
    while len(el) > 0:
      cutoff = min(420, len(el))
      msg = el[0:cutoff]
      el = el[cutoff:]
      sendIrcCommand('PRIVMSG '+chan+' :'+msg+' \r\n')


## Generic input message handling


def getName(line):
  # assumes format :[name]!blahblah
  return line[1:line.find('!')] 


def getMsg(line, respond=True):
  # returns the contents of a message, and the channel(or user) it was send to
  # assumes format "PRIVMSG #channel :[message]"
  # or "PRIVMSG user :[message]"
  m = line.split('PRIVMSG ')
  if len(m)>1:
    n = m[1].split(' :')
    msg = n[1]
    chan = n[0]
    if chan[0]!= '#': # for PM, get the sender. Otherwise the bot just starts talking to itself.
      chan = getName(line)
    if respond and chan == channel: # only respond to things in main channel. 
      #TODO: maybe respond in same channel as things were said? global prev list anyway?
      maybeRespond(getName(line), msg)
    return (chan, msg)
  else:
    return ("", "")


avgQuality = 5 # average quality of offered response (weighed exponentially heavily toward recent, 'cause fuck it)



def maybeRespond(name, msg):
  global prevWords, responses, avgQuality
  # responses is person talking to previous person talking to words said previously to word to say to frequency
  print "maybe responding"
  name = utils.getCanonicalName(name)
  prevWords[name] = utils.tokenizeLine(msg)
  if name and beingWho:
    score = 0
    modifier = {}
    for person in prevWords:
      for word in prevWords[person]:
        word = word.strip()
        if (beingWho in responses) and (person in responses[beingWho]) and (word in responses[beingWho][person]):
          print word
          for cword in responses[beingWho][person][word]:
            modifier[cword] = responses[beingWho][person][word][cword]**2 # TODO: +=, don't override
            score += modifier[cword]
    print modifier
    print('response score: '+ str(score))
    if score > 0:
      # TODO: factor response score into decision for whether to fire off the response?
      best = 0
      bestc = None
      for i in range(20):
        candidate = babble(beingWho, frequencies, modifier)
        cscore = 0
        cwords = utils.tokenizeLine(candidate)
        for cw in cwords:
          if cw in modifier:
            cscore += modifier[cw]
        length = len(cwords) - 2 # start and end token
        if length < 4 and re.search(r'[a-zA-z]+', candidate):
          print "length modifier"
          cscore += (4-length)**2
        print candidate, cwords, cscore
        if cscore > best:
          best = cscore
          bestc = candidate
      # chance to discard:
      threshold = randrange(avgQuality*2)
      if bestc:
        print bestc+': '+str(best)+' > '+str(threshold)+'?'
        if best > threshold:
          avgQuality = math.ceil(float(avgQuality+best)/2)
          print 'New average:', avgQuality
          sendMsg(bestc)
          prevWords = {}
        else:
          avgQuality = math.ceil(float(avgQuality*2+best)/3) # TODO: evaluate
          print 'updated average:', avgQuality


def getFirstWordAndRest(line):
  # same assumption as getMsg
  # NOTE: this means it assumes that line is a whole irc line, not an arbitrary string.
  # i.e. PRIVMSG etc.
  return getMsg(line, False)[1].split(None,1) # TODO: don't use getMsg? work on line only?



#### main

def main():
  global channel, botnick
  # process command-line arguments
  # TODO(yanamal): look into better argument syntax?
  
  if len(sys.argv) > 1:
    channel = '#' + sys.argv[1]
  
  if len(sys.argv) > 2:
    botnick = sys.argv[2]
    
  # load data from file(s)
  initializeData()
  
  # start bot
  connectAndJoin()
  inputLoop()


if __name__ == "__main__":
  main()
