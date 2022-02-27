import os
from datetime import datetime, timedelta

import numpy as np
import requests
from dotenv import load_dotenv
from flask import Flask, redirect, request, session

import helpers as hp
from tokens_storage import TokensStorage

load_dotenv()  # load environment variables

# client info
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')  # URI to redirect to after granting user permission
USER_ID = os.getenv('SPOTIFY_USER_ID')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
hp.open_browser()
token_store = TokensStorage()


@app.route('/')
def request_auth():
    # Auth flow step 1 - request authorization
    scope = 'user-top-read playlist-modify-public playlist-modify-private user-follow-read'
    return redirect(
        f'https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={scope}')


@app.route('/callback')
def request_tokens():
    # get code from spotify req param
    code = request.args.get('code')

    response = hp.post_mermer(code, REDIRECT_URI, CLIENT_ID, CLIENT_SECRET)
    hp.store_tokens(response)
    token_store.store_tokens(response)
    print(f' - Successfully completed Auth flow!')
    return redirect('/get_artists')


# Get user's followed artists
@app.route('/get_artists')
def get_artists():
    tokens = hp.get_tokens()
    hp.check_expiration(tokens)
    token_store.check_expiration(tokens)

    # Get request to followed artists endpoint
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
    response = hp.follow_artist_url(tokens)

    artist_ids = [artist['id'] for artist in response['artists']['items']]

    # While next results page exists, get it and its artist_ids
    while next_page_uri:= response['artists']['next']:
        r = requests.get(next_page_uri, headers=headers)
        response = r.json()
        artist_ids += [artist['id'] for artist in response['artists']['items']]

    print('Retrieved artist IDs!')
    session['artist_ids'] = artist_ids

    return redirect('/get_albums')


# Get all albums by followed artists (albums, singles)
@app.route('/get_albums')
def get_albums():
    tokens = hp.get_tokens()
    hp.check_expiration(tokens)
    token_store.check_expiration(tokens)

    artist_ids = session['artist_ids']
    album_ids = []
    album_names = {}  # used to check for duplicates with different id's * issue with some albums

    # set time frame for new releases (4 weeks)
    number_weeks = timedelta(weeks=4)
    time_frame = (datetime.now() - number_weeks).date()

    for id in artist_ids:
        response = hp.url_get_albums(id, tokens)
        albums = response['items']
        for album in albums:
            # check for tracks that are new releases (4 weeks)
            try:
                release_date = datetime.strptime(album['release_date'],
                                                 '%Y-%m-%d')  # convert release_date string to datetime
            except ValueError:
                # there appear to be some older release dates that only contain year (2007) - irrelevant
                print(f'Release date found with format: {album["release_date"]}')
                continue

            album_name = album['name']
            artist_name = album['artists'][0]['name']
            if release_date.date() > time_frame:
                # if we do find a duplicate album name, check if it's by a different artist
                if album_name not in album_names or artist_name != album_names[album_name]:
                    album_ids.append(album['id'])
                    album_names[album_name] = artist_name

    session['album_ids'] = album_ids
    print('Retrieved album IDs!')
    return redirect('/get_tracks')


# Get each individual "album's" track uri's
@app.route('/get_tracks')
def get_tracks():
    tokens = hp.get_tokens()
    hp.check_expiration(tokens)
    album_ids = session['album_ids']
    track_uris = []

    for id in album_ids:
        response = hp.require_tracks(id, tokens)

        track_uris += [track['uri'] for track in response['items']]

    hp.store_track_uris(track_uris)
    print('Retrieved tracks!')

    return redirect('/create_playlist')


# Create a new playlist in user account
@app.route('/create_playlist')
def create_playlist():
    tokens = hp.get_tokens()
    hp.check_expiration(tokens)

    response = hp.post_create_playlist(USER_ID, tokens)

    session['playlist_id'] = response['id']  # store our new playlist's id
    session['playlist_url'] = response['external_urls']['spotify']  # store new playlist's url

    print(f' - Created playlist!')
    return redirect('/add_to_playlist')


# Add new music releases to our newly created playlist
@app.route('/add_to_playlist')
def add_to_playlist():
    tokens = hp.get_tokens()
    hp.check_expiration(tokens)
    playlist_id = session['playlist_id']
    track_uris = hp.get_track_uris()

    # split up the request if number of tracks is too big. Spotify API max 100 per req.
    tracks_list = track_uris['uris']
    number_of_tracks = len(tracks_list)

    # split track_uris list into 3 sub lists
    if number_of_tracks > 200:
        three_split = np.array_split(tracks_list, 3)
        test = hp.final_list(tracks_list, 3)
        for lst in three_split:
            hp.add_tracks(tokens, playlist_id, list(lst))

    # split track_uris list into 2 sub lists
    elif number_of_tracks > 100:
        two_split = np.array_split(tracks_list, 2)
        test = hp.final_list(tracks_list, 2)
        for lst in two_split:
            hp.add_tracks(tokens, playlist_id, list(lst))

    else:
        hp.add_tracks(tokens, playlist_id, tracks_list)

    match number_of_tracks:
        case x if x > 200:
            pass
        case x if x > 100:
            pass
        case _:
            pass

    print('Added tracks to playlist!')

    # redirect to playlsit page & shut down flask server
    hp.shutdown_server(request.environ)
    return redirect(session['playlist_url'])


# Refresh access token near expiration
@app.route('/refresh')
def refresh_tokens():
    tokens = hp.get_tokens()

    response = hp.post_refresh(CLIENT_ID, CLIENT_SECRET, tokens)
    hp.refresh_tokens(response['access_token'], tokens['refresh_token'], response['expires_in'])

    print('Tokens refreshed!')
    return redirect('/get_artists')


if __name__ == '__main__':
    app.run()
