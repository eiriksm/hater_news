# -*- coding: utf-8 -*-
# Getting the guts of our app
from flask import Flask, render_template, request
# Setting up a connection to the internetz
from urllib2 import urlopen
# Getting things to come back from json to a dict
import json
# Making that json pretty if needed
from pprint import pprint
# Dealing with stupid Unicode issues
from django.utils.encoding import smart_str
# Bring me my Pickles, slave!
from sklearn.externals import joblib
# Importing my standard stuff
import pandas as pd
import numpy as np
# For troubleshooting
# Use This: code.interact(local=locals())
import code


# Building Out Some Functions to Ping The Hacker News API and Return Back Usable Lists Of Comments For Classifying

# Get all of a user's comments
def get_user_comments(username, reverse=False):
    comments = []
    ids = []
    reverse = ( reverse == 'true' )
    url_usr_strt = "https://hacker-news.firebaseio.com/v0/user/"
    url_itm_strt = "https://hacker-news.firebaseio.com/v0/item/"
    url_end = ".json"
    user = urlopen( url_usr_strt+username+url_end )
    user = json.loads( user.read() )
    if len(user['submitted']) > 45:
        if reverse == True:
            for c in user['submitted'][(len(user['submitted'])-46):len(user['submitted'])]:
                item = urlopen( url_itm_strt+str(c)+url_end )
                json_item = json.loads( item.read() )
                if 'text' in json_item:
                    print smart_str(json_item['id'])
                    ids.append(smart_str(json_item['id']))
                    print smart_str(json_item['text'])
                    comments.append(smart_str(json_item['text']))
        else:
            for c in user['submitted'][:46]:
                item = urlopen( url_itm_strt+str(c)+url_end )
                json_item = json.loads( item.read() )
                if 'text' in json_item:
                    print smart_str(json_item['id'])
                    ids.append(smart_str(json_item['id']))
                    print smart_str(json_item['text'])
                    comments.append(smart_str(json_item['text']))
    else:
        for c in user['submitted']:
            item = urlopen( url_itm_strt+str(c)+url_end )
            json_item = json.loads( item.read() )
            if 'text' in json_item:
                print smart_str(json_item['id'])
                ids.append(smart_str(json_item['id']))
                print smart_str(json_item['text'])
                comments.append(smart_str(json_item['text']))

    # comments = dict((k,v) for k,v in comments.iteritems() if v is not None)

    return { 'c':comments, 'id':ids }

# Get a final Hater Score. 100 is the worst, 0 is the best.
def calculate_score(predictions):
    total_score = []
    for s in predictions:
        total_score.append(s[1])

    return np.mean(total_score) * 100

# Get all a users comments and run them through my model
def user_score(comments, my_vect, clf):
    comments = filter(None, comments['c'])
    badwords = set(pd.read_csv('data/my_badwords.csv').words)
    badwords_count = []

    for el in comments:
        tokens = el.split(' ')
        badwords_count.append(len([i for i in tokens if i.lower() in badwords]))

    n_words = [len(c.split()) for c in comments]
    allcaps = [np.sum([w.isupper() for w in comment.split()]) for comment in comments]
    allcaps_ratio = np.array(allcaps) / np.array(n_words, dtype=np.float)
    bad_ratio = np.array(badwords_count) / np.array(n_words, dtype=np.float)
    exclamation = [c.count("!") for c in comments]
    addressing = [c.count("@") for c in comments]
    spaces = [c.count(" ") for c in comments]

    re_badwords = np.array(badwords_count).reshape((len(badwords_count),1))
    re_n_words = np.array(n_words).reshape((len(badwords_count),1))
    re_allcaps = np.array(allcaps).reshape((len(badwords_count),1))
    re_allcaps_ratio = np.array(allcaps_ratio).reshape((len(badwords_count),1))
    re_bad_ratio = np.array(bad_ratio).reshape((len(badwords_count),1))
    re_exclamation = np.array(exclamation).reshape((len(badwords_count),1))
    re_addressing = np.array(addressing).reshape((len(badwords_count),1))
    re_spaces = np.array(spaces).reshape((len(badwords_count),1))

    vect = my_vect.transform(comments)
    features = np.hstack((vect.todense(), re_badwords))
    features = np.hstack((features, re_n_words))
    features = np.hstack((features, re_allcaps))
    features = np.hstack((features, re_allcaps_ratio))
    features = np.hstack((features, re_bad_ratio))
    features = np.hstack((features, re_exclamation))
    features = np.hstack((features, re_addressing))
    features = np.hstack((features, re_spaces))
    predictions = clf.predict_proba(features)

    return predictions



# Setting up app
app = Flask(__name__)


print 'Loading clf & vect...'
vect = joblib.load('vect.pkl')
clf = joblib.load('clf.pkl')
print 'All loaded Captn\'!'

# Setting up our base route
@app.route('/')
def display_form():
    return render_template('hater-form.html')

# Setting up a way to get our form data
@app.route('/hater-score', methods=['POST'])
def predict_hate():
    # Saving our data from the form so we can use it.
    username = request.form['username']
    comments = []
    print request
    reverse = request.form['reverse']
    temp = get_user_comments(username, reverse=reverse)
    text = filter(None, temp['c'])
    predictions = user_score(temp, vect, clf)
    ids = temp['id']
    colors = []

    for p in predictions:
        # if p[1] > .2:
            # colors.append( "rgba(89, 255, 160, "+str(p[0]+.01)+")" )
        # else:
        colors.append( "rgba(255, 89, 89, "+str(p[1]+.01)+")" )


    for i, v in enumerate(text):
        comments.append({'score': predictions[i-1][1]+.05, 'id': ids[i-1], 'comment': text[i-1], 'color': colors[i-1] })

    worst_comment = sorted(comments, key=lambda k: k['score'])
    hater_level = [(calculate_score(predictions)/100), (1-(calculate_score(predictions)/100))]

    print 'predicting hater score for %s' % username
    d = {
        'username': username,
        'comments': comments,
        'score': calculate_score(predictions),
        'hater_level': hater_level[0],
        'lover_level': hater_level[1],
        'worst_comment': worst_comment[-1]
    }
    return render_template('hater-score.html', d=d)

if __name__ == '__main__':
    # app.debug = True
    app.run()
