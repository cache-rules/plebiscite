import argparse
import json

from waitress import serve

from app import App

parser = argparse.ArgumentParser(description='Start a plebiscite web server')
parser.add_argument('config', help='Path to the config.json file used to configure the server')


def read_config():
    """
    Reads the specified config file from disk and parses it as JSON.

    :return:
    """
    args = parser.parse_args()

    with open(args.config, mode='r') as f:
        config = json.load(f)

    return config


def run():
    """
    Bootstraps an App and serves it with waitress.

    :return:
    """
    config = read_config()
    app = App(config)
    server_config = config['server']
    serve(app.flask_app, host=server_config['host'], port=server_config['port'], threads=8)


if __name__ == '__main__':
    run()
