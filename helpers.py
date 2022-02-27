import base64
import json
import webbrowser
from datetime import date

import requests
from flask import redirect

# spotify API endpoints
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
MY_FOLLOWED_ARTISTS_URL = 'https://api.spotify.com/v1/me/following?type=artist'

TOKENS_FILE = 'tokens.json'
TRACK_URI_FILE = 'track_uris.json'
LOCAL_SERVER = 'http://127.0.0.1:5000/'
# open browser at address where app is running locally
def open_browser():
    try:
        url = LOCAL_SERVER
        webbrowser.open(url)
    except Exception:
        print(f'You need to manually open your browser and navigate to: {LOCAL_SERVER}')

# get access/refresh tokens
def get_tokens():
    print('--get_tokens')
    with open(TOKENS_FILE, 'r') as openfile:
        tokens = json.load(openfile)
    return tokens

# store access/refresh tokens
def store_tokens(response_data):
    print('--store_tokens')
    tokens = {
        'access_token': response_data['access_token'],
        'refresh_token': response_data['refresh_token'],
        'expires_in': response_data['expires_in']
    }
    with open(TOKENS_FILE, 'w') as outfile:
        json.dump(tokens, outfile)

# refresh tokens
def refresh_tokens(access_token, refresh_token, expires_in):
    print('--refresh_tokens')

    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': expires_in
    }
    with open(TOKENS_FILE, 'w') as outfile:
        json.dump(tokens, outfile)

# check access token expiration
def check_expiration(tokens):
    if tokens['expires_in'] < 100:
        return redirect('/refresh')


# store track_uris in a dictionary
def store_track_uris(track_uris):
    uri_dict = {'uris': track_uris}
    with open(TRACK_URI_FILE, 'w') as outfile:
        json.dump(uri_dict, outfile)

# retrieve track_uris
def get_track_uris():
    with open(TRACK_URI_FILE, 'r') as openfile:
        uri_dict = json.load(openfile)
    return uri_dict

# post request to add tracks to playlist
def add_tracks(tokens, playlist_id, tracks_list):
    uri = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {tokens["access_token"]}', 'Content-Type': 'application/json'}
    payload = {'uris': tracks_list}
    requests.post(uri, headers=headers, data=json.dumps(payload))

def post_create_playlist(user_id, tokens):
    current_date = (date.today()).strftime('%m-%d-%Y')
    playlist_name = f'New Monthly Releases - {current_date}'

    # make request to create_playlist endpoint
    uri = f'https://api.spotify.com/v1/users/{user_id}/playlists'
    headers = {'Authorization': f'Bearer {tokens["access_token"]}', 'Content-Type': 'application/json'}
    payload = {'name': playlist_name}
    r = requests.post(uri, headers=headers, data=json.dumps(payload))
    return r.json()

def url_get_albums(id, tokens):
    uri = f'https://api.spotify.com/v1/artists/{id}/albums?include_groups=album,single&country=US'
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
    r = requests.get(uri, headers=headers)
    return r.json()

def require_tracks(id, tokens):
    uri = f'https://api.spotify.com/v1/albums/{id}/tracks'
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
    r = requests.get(uri, headers=headers)
    return r.json()

def post_refresh(client_id, client_secret, tokens):
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    }
    base64encoded = str(base64.b64encode(f'{client_id}:{client_secret}'.encode('ascii')), 'ascii')
    headers = {'Authorization': f'Basic {base64encoded}'}

    # post request for new tokens
    r = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
    return r.json()

def post_mermer(code, redirect_uri, client_id, client_secret):
    # necessary request body params
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    # Auth flow step 2 - request refresh and access tokens
    r = requests.post(SPOTIFY_TOKEN_URL, data=payload)
    return r.json()

def follow_artist_url(tokens):
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
    r = requests.get(MY_FOLLOWED_ARTISTS_URL, headers=headers)
    return r.json()

# Shut down the flask server
def shutdown_server(environ):
    # look for dev server shutdown function in request environment
    if not 'werkzeug.server.shutdown' in environ:
        raise RuntimeError('Not running the development server')
    environ['werkzeug.server.shutdown']() # call the shutdown function
    print('Shutting down server...')

final_list= lambda test_list, x: [test_list[i:i+x] for i in range(0, len(test_list), x)]
