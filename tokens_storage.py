import json

from werkzeug.utils import redirect

TOKENS_FILE = 'tokens.json'


class TokensStorage:
    def __init__(self):
        self.__tokens = None
        self.__cache = None

    # get access/refresh tokens
    def get_tokens(self):
        print('--get_tokens')

        if self.__tokens == self.__cache:
            print('-- get_tokens: return what is saved in cache!')
            return self.__tokens

        with open(TOKENS_FILE, 'r') as openfile:
            self.__cache = self.__tokens = json.load(openfile)

        print('-- get_tokens: return what is saved in file!')
        return self.__tokens

    # store access/refresh tokens
    def store_tokens(self, response_data):
        print('--store_tokens')
        self.__tokens = {
            'access_token': response_data['access_token'],
            'refresh_token': response_data['refresh_token'],
            'expires_in': response_data['expires_in']
        }
        with open(TOKENS_FILE, 'w') as outfile:
            json.dump(self.__tokens, outfile)

    # refresh tokens
    def refresh_tokens(self, access_token, refresh_token, expires_in):
        print('--refresh_tokens')

        self.__tokens = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in
        }
        with open(TOKENS_FILE, 'w') as outfile:
            json.dump(self.__tokens, outfile)

    # check access token expiration
    def check_expiration(self, tokens):
        if self.__tokens['expires_in'] < 100:
            return redirect('/refresh')
