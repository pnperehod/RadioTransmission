import os, sys
import configparser
import discogs, mp4tags

oauth2_info = {'consumer_key': '',
               'consumer_secret': '',
               'oauth_token': '',
               'oauth_token_secret': ''}

def config_read():
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        oauth2_info['consumer_key'] = config['authentication']['consumer_key']
        oauth2_info['consumer_secret'] = config['authentication']['consumer_secret']
        oauth2_info['oauth_token'] = config['authentication']['oauth_token']
        oauth2_info['oauth_token_secret'] = config['authentication']['oauth_token_secret']
    except:
        sys.exit(f"Can't read config file or syntax error")


def main():
    if (len(sys.argv) < 2):
        print('Usage: m4aplusinfo <SourceDir>')
        return

    Sourcedir = sys.argv[1]
    config_read()
    client = discogs.connect_oauth(oauth2_info)


    update_counter = 0

    for dirpath, dirnames, fnames in os.walk(Sourcedir, True):
        for fname in fnames:
            name, extension = os.path.splitext(fname)
            if extension != '.m4a':
                continue
            number = name.split('_')[0]
            song_title = name.split('_')[1]
            mp4tags.fill_mp4_tags(song_title, os.path.join(dirpath, fname), client)



if __name__ == '__main__':
    main()
