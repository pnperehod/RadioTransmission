import io
import json
import time

import oauth2 as oauth
from PIL import Image
import unidecode as unidec
from datetime import datetime

base_url = 'https://api.discogs.com/database/search?q='
release_url = 'https://api.discogs.com/releases/'
cover_file = 'cover.jpg'
user_agent = 'detektor_radio'
viewer = None
release_info = {'album_name': '', 'year': ''}
proper_formats = ['lp', 'cd', 'cdr', 'file', 'vinyl', 'compilation']



def connect_oauth(oauth_info):

    # create oauth Consumer and Client objects using
    consumer = oauth.Consumer(oauth_info['consumer_key'], oauth_info['consumer_secret'])

    token = oauth.Token(key=oauth_info['oauth_token'], secret=oauth_info['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    return client

def site_request(url, uagent, client):
    tries = 5
    while tries > 0:
        try:
            resp, content = client.request(url, headers={'User-Agent': uagent})
        except Exception as e:
            print(e)
            tries = tries - 1
            time.sleep(3)
            continue
        break
    if tries == 0:
        return None, None
    if resp['status'] != '200':
        return None, None
    return resp, content

def do_the_search(artist, title, client):
    search_url = base_url + '+'.join(artist.split()) + '+' + '+'.join(title.split()) + '&page=1&per_page=100'
    resp, content = site_request(search_url, user_agent, client)
    return resp, content

def no_comma(str):                  # for artist names like surname, name
    is_comma = str.find(',')
    if is_comma != -1:
        str = str[is_comma + 1:].strip() + ' ' + str[:is_comma].strip()
    return str

def no_brackets(str, brackets):
    open_bracket = str.find(brackets[0])
    close_bracket = str.find(brackets[1])
    if open_bracket != -1 and close_bracket != -1:
        str = str[:open_bracket].strip() + str[close_bracket + 1:]
    return str


def correct_name(str):
    str = str.replace('&', '%26')   # & -> %26
    str = str.replace("\'", '%27')  # ' -> %27
    str = str.split('|')[1] if '|' in str else str
    str = no_brackets(str, '[]')
    str = unidec.unidecode(str)
    return str.strip()

def correct_artist_name(str):
    str = correct_name(str)
    if str.find('The') == 0:                # if The at the name's start
        str = str.replace('The', '', 1)     # remove "The" in artist's name
# removed everything  in brackets (not good enough)
    str = no_brackets(str, '()')
    str = no_brackets(str, '[]')
    str = no_brackets(str, '{}')
    str = no_comma(str)
    str = str[:-1] if (len(str) > 0) and ('*' == str[-1]) else str     # if last symbol in the artist name is '*', remove it
    return str.strip()

def is_proper_format(media_type):
    for f in proper_formats:
        if f in media_type:
            return True
    return False


def get_proper_release(artist, release, media_format, albums_only):
    items = int(release['pagination']['items'])
    per_page = int(release['pagination']['per_page'])
    variants = items if items < per_page else per_page
    year_min = 9999
    pointer = -1
    for i in range(variants):
        try:
            year = int(release['results'][i]['year'])
            media_type = release['results'][i]['format']
            main_artist = release['results'][i]['title']
        except:
            continue
        main_artist = main_artist.split(' - ')[0]
        main_artist = correct_artist_name(main_artist).lower()
        artist = correct_artist_name(artist).lower()
        for med in range(len(media_type)):
            media_type[med] = media_type[med].lower()

        if media_format == 'compilation':
            creators = ((artist in main_artist) or (main_artist == 'various'))
        else:
            creators = (artist in main_artist)

        consider_albums = (not albums_only) or ('album' in media_type)

        if ((media_format in media_type) and ('compilation' not in media_type) and consider_albums):
            formats_filter = True
        elif (media_format == 'compilation') and (media_format in media_type):
            formats_filter = True
        else:
            formats_filter = False

        if creators:
            if (year < year_min) and formats_filter:
                year_min = year
                pointer = i
            else:
                continue
    return pointer

def search_artist(artist, client):
    artist = correct_artist_name(artist)
    search_url = base_url + '+'.join(artist.split()) + '&type=artist'
    resp, content = site_request(search_url, user_agent, client)
    return resp, content

def get_album_cover(song_title, client):
    if '-' not in song_title:
        return False
    try:
        artist = song_title.split(' - ')[0]         ##
        title = song_title.split(' - ')[1]          ## Due to some crazy radio station
    except:
        return False
    artist_web = correct_artist_name(artist)
    title_web = correct_name(title)
    if artist_web == '' or title_web == '':
        return False

# check if artist really exists
    while artist_web != '':
        resp, content = search_artist(artist_web, client)
        if content == None:
            return False
        release = json.loads(content.decode('utf-8'))
        if release['pagination']['items'] != 0:
            break
        artist_web = ' '.join(artist_web.split()[:-1])
        if artist_web == '':
            return False

    resp, content = do_the_search(artist_web, title_web, client)
    if content == None:
        print('Invalid API response {0}.'.format(resp['status']))
        return False
    release = json.loads(content.decode('utf-8'))
    if release['pagination']['items'] == 0:              # nothing was found
        return False

# ---------------------- release check --------------------------------
    albums_only = True
    for media_format in proper_formats:
        pointer = get_proper_release(artist_web, release, media_format, albums_only)      # compilations not valid
        if pointer == -1:           # this media_format hasn't been found
            continue
        else:
            break
    if pointer == -1:
        albums_only = False
        for media_format in proper_formats:
            pointer = get_proper_release(artist_web, release, media_format, albums_only)
            if pointer == -1:
                continue
            else:
                break

    if pointer == -1:
        return False                # found nothing at all

    cover_image = release['results'][pointer]['cover_image']
    try:
        release_info['album_name'] = release['results'][pointer]['title']
    except:
        release_info['album_name'] = ''
    try:
        release_info['year'] = release['results'][pointer]['year']
    except:
        release_info['year'] = ''

    try:
        resp, content = client.request(cover_image, headers={'User-Agent': user_agent})
    except Exception as e:
        print(f'Unable to download image {cover_image}, error {e}')
        return False
    img = Image.open(io.BytesIO(content))
    try:
        img.save(cover_file)
    except OSError:
        print(f'Cant write file {cover_file} for {song_title}')
    return True

def get_release_info():
    return release_info['album_name'], release_info['year']


def main():
    pass

if __name__ == '__main__':
    main()
