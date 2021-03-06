"""
AA
05-11-2018

Starting from a database with no retweets (only their original tweets) and no
duplicates, a database consisting only of personal tweets will be created by:

- Classifying each user: personal (1) or institutions (0)
- Calculating average score for all tweets of a user
    -> exclude users with a score <0.25 as institutions

- Classify each tweet: personal (1) or institution (0)
"""
import argparse
from pprint import pprint
import numpy as np
import scipy
import pandas as pd
import sys
import os
import os.path as op
from sklearn.externals import joblib
from gensim.models import FastText

# add path to utils module to python path
basename = op.split(op.dirname(op.realpath(__file__)))[0]
path_utils = op.join(basename , "utils")
sys.path.insert(0, path_utils)

from sys_utils import load_library
from tweet_utils import tweet_vectorizer

load_library(op.join(basename, 'readWrite'))
load_library(op.join(basename, 'preprocess'))
from preprocess import Preprocess
from readWrite import savePandasDFtoFile, readFile



prep = Preprocess()


def preprocess_tweet(tweet):
    return prep.tokenize(tweet)

def score_users(tweets, model_user_classif, wordEmbedding, user_name, score_personal_minimum=0.25, textColumn="tweet"):
    """
        Calculates score for each user and excludes user with a score < score_personal_minimum
        as institutions. The score is the mean over the classification result of
        all tweets of a user, where the a personal user : 1 and a institution : 0
    """
    print("Number raw tweets:", len(tweets))

    tweets_user_pers = tweets.groupby(by=user_name).filter(lambda userTweets: np.mean([model_user_classif.predict(\
                                                                 tweet_vectorizer(preprocess_tweet(tweet), wordEmbedding).reshape(1, -1))\
                                                                 for tweet in userTweets[textColumn].values]) >= score_personal_minimum)

    return tweets_user_pers
#    for i, (userName, userTweets) in enumerate(tweets.groupby(by=user_name)):
#        if i % 1000 == 0:
#            print(userName, np.mean([model_user_classif.predict(tweet_vectorizer(preprocess_tweet(tweet), wordEmbedding).reshape(1, -1)) for tweet in userTweets[textColumn].values]))
#            for tweet in userTweets[textColumn].values:
#                print(tweet)
#            print() 
#        
#        if i == 1000000:
#            break


#def f(tweet, wordEmbedding, model_tweet_classif):
#    tweet = tweet_vectorizer(preprocess_tweet(tweet), wordEmbedding)
#    tweet = tweet.reshape(1, -1)
#    predict = model_tweet_classif.predict(tweet)
#    print("predict:", predict)
#    return predict[0]

def get_personal_tweets(tweets, model_tweet_classif, wordEmbedding, textColumn="text"):
    """
        From the given database with personal users, get only personal tweets
        Remark: A personal user can tweet personal and institutional!
    """
#    tweets = tweets[textColumn]
#    tweets = tweets.apply(lambda tweet: f(tweet, wordEmbedding, model_tweet_classif) == 1)
#    return tweets
    return tweets[tweets[textColumn] \
                .apply(lambda tweet: model_tweet_classif.predict(tweet_vectorizer(preprocess_tweet(tweet), wordEmbedding).reshape(1, -1))[0] == 1)]

    


if __name__ == '__main__':


    parser = argparse.ArgumentParser(description="Obtaining database with only personal tweets",
                                     epilog='Example usage in local mode : \
                                             python personal_tweets.py -m "local"  \
                                             -puc "P_A_T_H" -ptc "P_A_T_H" -pwe "P_A_T_H" \
                                             -pdata "P_A_T_H" -sm 0.25 -s "P_A_T_H" \
                                      ')
    parser.add_argument("-m", "--mode", help="Mode of execution (default=local)", choices=["local", "cluster"], required=True, default="local")
    parser.add_argument("-puc", "--pathUserClassifier", help="Path to the user classifier (personal vs institutional)", required=True)
    parser.add_argument("-ptc", "--pathTweetClassifier", help="Path to the tweet classifier (personal vs institutional)", required=True)
    parser.add_argument("-pwe", "--pathWordEmbedding", help="Path to the word embeddings", required=True)
    parser.add_argument("-pdata", "--pathData", help="Path to the data to classify", required=True)
    parser.add_argument("-sm", "--scorePersonalMinimum", help="Minimum mean-score [0,1] over all tweets per user. \
                                                                Users are excluded with a mean score less than the provided one. Default=0.25", default=0.25, type=float)
    parser.add_argument("-s", "--pathSave", help="Path to save personal database to (.parquet or .csv)")
    parser.add_argument("-tn", "--columnNameTextData", help="Column name of the text data", default="tweet")
    parser.add_argument("-unc", "--userNameColumn", help="Give the user_name column (default: user_screen_name)", default="user_screen_name")

    args = parser.parse_args()

    print("Load user classifier..")
    #loaded_model = joblib.load(filename)
    model_user_classif = joblib.load(args.pathUserClassifier)

    print("Load tweet classifier..")
    model_tweet_classif = joblib.load(args.pathTweetClassifier)

    print("Load word embedding..")
    wordEmbedding = FastText.load(args.pathWordEmbedding)

    print("Load data..")
    tweets = readFile(args.pathData)

    print("Classify all tweets of an user and exclude all users with a mean score < {} ...".format(args.scorePersonalMinimum))
    tweets_user_pers = score_users(tweets, model_user_classif, wordEmbedding, args.userNameColumn, score_personal_minimum=args.scorePersonalMinimum, textColumn=args.columnNameTextData)
    print("Number tweets personal users:", len(tweets_user_pers))

    print("Classify only personal tweets of personal users..")
    tweets_personal = get_personal_tweets(tweets_user_pers, model_tweet_classif, wordEmbedding, textColumn=args.columnNameTextData)
    print("Number personal tweets:", len(tweets_personal))
    print(tweets_personal.head())

    print("Save personal tweets to file {}  ...".format(args.pathSave))
    savePandasDFtoFile(tweets_personal, args.pathSave)
