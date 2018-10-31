import argparse
import random

import requests
import time

parser = argparse.ArgumentParser(description='Populate a plebiscite election')
parser.add_argument('url', help='The url of the plebiscite server')
parser.add_argument('phone', help='The phone number of the admin')
parser.add_argument('options', help='The path to the options file containing one option per line')


def fake_phone():
    digits = []

    for i in range(0, 10):
        digits.append(str(random.randrange(0, 9)))

    return f'+1{"".join(digits)}'


def load_file(path):
    options = []

    with open(path, mode='r') as f:
        for line in f:
            line = line.strip()

            if len(line) > 0:
                options.append(line)

    return options


def setup_ballot(sms_url, phone, options):
    r = requests.post(sms_url, data={'Body': 'reset', 'From': phone})
    print(r.text)

    for option in options:
        r = requests.post(sms_url, data={'Body': f'add {option}', 'From': phone})
        print(r.text)

    r = requests.post(sms_url, data={'Body': 'enable 6', 'From': phone})
    print(r.text)


def cast_votes(sms_url, options_len):
    for i in range(0, 20):
        phone = fake_phone()

        for j in range(0, 2):
            choice = str(random.randrange(0, options_len))
            r = requests.post(sms_url, data={'Body': choice, 'From': phone})
            print(r.text)
            time.sleep(0.3)


def test_other_functions(sms_url, admin_phone):
    phone = fake_phone()

    r = requests.post(sms_url, data={'Body': '-1', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'totally invalid', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': '6.7', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': '√', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'import this', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'import antigravity', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'puppy', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'ballot', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'status', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'status', 'From': admin_phone})
    print(r.text)


def test_remove(sms_url, phone, options):
    r = requests.post(sms_url, data={'Body': 'add Alan Vezina', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': f'{len(options)}', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': f'{len(options)}', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'STATUS', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': f'remove {len(options)}', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'status', 'From': phone})
    print(r.text)

    r = requests.post(sms_url, data={'Body': 'ballot', 'From': phone})
    print(r.text)


def run():
    args = parser.parse_args()
    sms_url = f'{args.url}/sms'
    options = load_file(args.options)
    setup_ballot(sms_url, args.phone, options)
    cast_votes(sms_url, len(options))
    test_remove(sms_url, args.phone, options)
    test_other_functions(sms_url, args.phone)


if __name__ == '__main__':
    run()
