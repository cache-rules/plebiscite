import random
from datetime import datetime, timedelta
import os
from functools import cmp_to_key
from threading import RLock

from flask import Flask, jsonify
from flask import render_template
from flask import request
from twilio import twiml
from twilio.rest import TwilioRestClient

zen_lines = [
    'Beautiful is better than ugly.',
    'Explicit is better than implicit.',
    'Simple is better than complex.',
    'Complex is better than complicated.',
    'Flat is better than nested.',
    'Sparse is better than dense.',
    'Readability counts.',
    'Special cases aren\'t special enough to break the rules.\nAlthough practicality beats purity.',
    'Errors should never pass silently.\nUnless explicitly silenced.',
    'In the face of ambiguity, refuse the temptation to guess.',
    'There should be one-- and preferably only one --obvious way to do it.\nAlthough that way may not be obvious at first unless you\'re Dutch.',
    'Now is better than never.\nAlthough never is often better than *right* now.',
    'If the implementation is hard to explain, it\'s a bad idea.',
    'If the implementation is easy to explain, it may be a good idea.',
    'Namespaces are one honking great idea -- let\'s do more of those!',
]


def zen(phone, body):
    return random.choice(zen_lines)


def antigravity(phone, body):
    return 'https://xkcd.com/353/'


def puppy(phone, body):
    return 'The best meetup in town!'


def xyzzy(phone, body):
    return (
        'YOU ARE STANDING AT THE END OF A ROAD BEFORE A SMALL BRICK BUILDING. '
        'AROUND YOU IS A FOREST.  A SMALL STREAM FLOWS OUT OF THE BUILDING AND '
        'DOWN A GULLY.'
    )

maze_responses = [
    'A HOLLOW VOICE SAYS "PLUGH".',
    'YOU ARE IN A MAZE OF TWISTY LITTLE PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A LITTLE MAZE OF TWISTING PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A MAZE OF TWISTING LITTLE PASSAGES, ALL DIFFERENT.',
    'A HOLLOW VOICE SAYS "PLUGH".',
    'YOU ARE IN A LITTLE MAZE OF TWISTY PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A TWISTING MAZE OF LITTLE PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A TWISTING LITTLE MAZE OF PASSAGES, ALL DIFFERENT.',
    'A HOLLOW VOICE SAYS "PLUGH".',
    'YOU ARE IN A TWISTY LITTLE MAZE OF PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A TWISTY MAZE OF LITTLE PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A LITTLE TWISTY MAZE OF PASSAGES, ALL DIFFERENT.',
    'A HOLLOW VOICE SAYS "PLUGH".',
    'YOU ARE IN A MAZE OF LITTLE TWISTING PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A MAZE OF LITTLE TWISTY PASSAGES, ALL DIFFERENT.',
    'YOU ARE IN A MAZE OF TWISTY LITTLE PASSAGES, ALL ALIKE.',
    'YOU ARE AT WITT\'S END.  PASSAGES LEAD OFF IN *ALL* DIRECTIONS.',
    'A HOLLOW VOICE SAYS "PLUGH".',
]


def move_direction(phone, body):
    return random.choice(maze_responses)


def pip_freeze(phone, body):
    return (
        'Flask==0.12\n'
        'twilio==5.7.0\n'
        'waitress==1.0.2\n'
    )


def license(phone, body):
    return (
        'Apache License\n'
        'Version 2.0, January 2004\n'
        'http://www.apache.org/licenses/\n'
    )


def python_version(phone, body):
    return (
        'Python 3.6.0\n'
        '[GCC 4.9.2] on linux\n'
        'Type "help", "copyright", "credits" or "license" for more information.\n'
        '>>>'
    )


def results_comparator(a, b):
    votes_a = len(a['votes'])
    votes_b = len(b['votes'])

    if votes_a < votes_b:
        return 1
    elif votes_a > votes_b:
        return -1

    return 0


results_key = cmp_to_key(results_comparator)


class App:
    """
    App is a class that contains everything needed to bootstrap a Flask application and serve the metrics server.
    """
    def __init__(self, config):
        # TODO: add easter eggs from config as well.
        self.req_counter = 0
        self.req_lock = RLock()
        self.config = config
        self.admin = config.get('admin')
        self.phone = self.config['twilio']['phone']
        self.twilio = TwilioRestClient(self.config['twilio']['account_sid'], self.config['twilio']['token'])
        self.results = {}
        self.voters = {}
        self.admin_cmds = {
            'enable': self.start_election,
            'disable': self.stop_election,
            'reset': self.reset_election,
            'add': self.add_option,
            'status': self.status,
        }
        self.special_commands = {
            'import this': zen,
            'import antigravity': antigravity,
            'puppy': puppy,
            'xyzzy': xyzzy,
            'go north': move_direction,
            'go east': move_direction,
            'go south': move_direction,
            'go west': move_direction,
            'pip freeze': pip_freeze,
            'license': license,
            'python': python_version,
            'ballot': self.help,
        }
        self.election_expiration = None
        self.voter_lock = RLock()
        self.init_flask_app()

    def init_flask_app(self):
        self.flask_app = Flask(__name__, template_folder=os.path.realpath('./templates'), static_folder='./static')
        self.flask_app.debug = True
        self.flask_app.add_url_rule('/', view_func=self.index, methods=['GET'])
        self.flask_app.add_url_rule('/status', view_func=self.status_get, methods=['GET'])
        self.flask_app.add_url_rule('/options', view_func=self.add_option_post, methods=['POST'])
        self.flask_app.add_url_rule('/start', view_func=self.start_election_post, methods=['POST'])
        self.flask_app.add_url_rule('/sms', view_func=self.sms_post, methods=['POST'])
        self.flask_app.add_url_rule('/reset', view_func=self.reset_election_post, methods=['POST'])

    def serialize_results(self):
        results = []

        for k, v in self.results.items():
            results.append({'name': v['name'], 'value': k, 'votes': len(v['votes'])})

        return results

    def index(self):
        return render_template('index.html', requests=self.req_counter, voters=len(self.voters),
                               results=self.serialize_results(), phone=self.phone)

    def status_get(self):
        return jsonify(requests=self.req_counter, voters=len(self.voters), results=self.serialize_results())

    def help(self, phone, body):
        if self.election_expiration is None:
            return 'Election is currently closed.'

        msg = 'To vote text the number you see to the left of the options below:\n'
        options = ''

        for idx, option in enumerate(self.results.values()):
            options += f'\t{idx}\t-\t{option["name"]}\n'

        voter = self.voters.get(phone, {'votes': []})
        msg += options + f'You have {2 - len(voter["votes"])} votes left'

        return msg

    def vote(self, phone, body):
        now = datetime.now()

        if self.election_expiration is not None and self.election_expiration < now:
            self.election_expiration = None

        if self.election_expiration is None:
            return 'The election is currently closed.'

        option = self.results.get(body, None)

        if option is None:
            return 'Does not compute. Type "ballot" to see available options.'

        with self.voter_lock:
            if self.voters.get(phone, None) is None:
                self.voters[phone] = {'votes': []}

            voter = self.voters[phone]

            if len(voter['votes']) == 2:
                return 'Vote not recorded, no votes left.'
            else:
                voter['votes'].append(body)
                option['votes'].append(phone)
                name = option['name']
                votes_left = 2 - len(voter["votes"])

                return f'We have recorded your vote for {name}! You have {votes_left} votes left.'

    def start_election(self, parts):
        """
        Starts the election, allowing people to vote on the available options.
        :return:
        """
        if not isinstance(parts, str):
            parts = ' '.join(parts)

        if parts == '':
            duration = 0
        else:
            duration = int(parts)

        self.election_expiration = datetime.now() + timedelta(hours=duration)

        return f'Election will expire at {self.election_expiration.isoformat()}.'

    def stop_election(self, *args):
        """
        Stops the election, but does not clear any options or results.
        :return:
        """
        self.election_expiration = None

        return 'Election stopped.'

    def add_option(self, parts):
        """
        Adds single option to election.
        :return:
        """
        if not isinstance(parts, str):
            parts = ' '.join(parts)

        with self.voter_lock:
            self.results[str(len(self.results))] = {'name': parts, 'votes': []}

        return f'{parts} has been added.'

    def reset_election(self, *args):
        """
        Combines stops the election and removes all options.
        :return:
        """
        with self.voter_lock:
            self.results = {}
            self.voters = {}
            self.election_expiration = None

        return 'Election reset.'

    def status(self, *args):
        """
        TODO: return the following:
            - total requests made
            - total votes cast
            - total voters
            - current rankings
        :return:
        """
        msg = (
            f'Reqs: {self.req_counter}\n'
            f'Voters: {len(self.voters)}\n'
        )
        results = 'Results:\n'
        counter = 0
        votes = sorted(self.results.values(), key=results_key)

        for option in votes:
            counter += len(option['votes'])
            # TODO: sort by most votes
            results += f'\t- {option["name"]}: {len(option["votes"])}\n'

        msg += f'Total Votes: {counter}\n' + results

        return msg

    def handle_admin(self, body):
        msg = None
        parts = body.split()
        cmd = parts[0].lower()
        handler = self.admin_cmds.get(cmd, None)

        if handler is not None:
            try:
                msg = handler(parts[1:])
            except Exception as e:
                print(f'Error processing admin request with fn {handler.__name__}', e)

        return msg

    def sms_post(self):
        with self.req_lock:
            self.req_counter += 1

        resp = twiml.Response()
        phone = request.form['From']
        body = request.form['Body'].strip()

        if phone == self.admin:
            msg = self.handle_admin(body)

            if msg is not None:
                resp.message(msg)
                return str(resp)

        handler = self.special_commands.get(body.lower(), self.vote)

        try:
            resp.message(handler(phone, body))
        except Exception as e:
            print(e)

        return str(resp)

    def add_option_post(self):
        opt = request.get_json().get('option', None)

        if opt is None:
            return jsonify(success=False, error='Body must include "option" parameter'), 400

        self.add_option(opt.strip())

        return jsonify(success=True, options=sorted(self.results.keys()))

    def start_election_post(self):
        self.start_election(request.get_json().get('duration', ''))

        return jsonify(success=True)

    def stop_election_post(self):
        self.stop_election()

        return jsonify(success=True)

    def reset_election_post(self):
        self.reset_election()

        return jsonify(success=True)
