#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import random

from time import sleep

from fabric.api import *
from fabric.context_managers import hide
from fabric.tasks import execute

from setting import user, password

env.hosts = ["140.112.29.201", "127.0.0.1"]
env.roledefs = {
    "alliance":   env.hosts,
}

env.user = user
env.password = password


addresses = {}
licenses = {}

NUM_ADDRESSES = 10
PORT = 55777
MATURITY = 12
NUM_COLORS = 1000
MINT_AMOUNT = 1000

class AutoTestError(Exception):

    def __init__(self, message):

        super(AutoTestError, self).__init__(message)

def cli(*args, **kwargs):
    return run("bitcoin-cli -gcoin " + ' '.join(map(str, args)))

def reset_bitcoind():

    run("killall -9 bitcoind")

    sleep(3)

    run("rm -rf $HOME/.bitcoin/gcoin")

    # TODO: if bitcoind has problem, e.g. Error: OpenSSL lack support for
    # ECDSA, we should handle error?
    result = run("bitcoind -gcoin -daemon -port={}".format(PORT))
    while True:
        result = cli("getinfo")
        if result.succeeded:
            return result
        sleep(1)

def add_peers():

    for host in env.hosts:
        # add peers except for myself
        if host != env.host:
            cli("addnode", "{}:{}".format(host, PORT), 'add')
            cli("addnode", "{}:{}".format(host, PORT), 'onetry')

def get_addresses():

    while True:
        result = cli("listwalletaddress", NUM_ADDRESSES)
        if result.succeeded:
            break
        sleep(1)

    result = json.loads(result)
    return [str(i) for i in result]

@parallel
def setup_connections():
    """
        1. setup bitcoinds
        2. connect peers
        3. get addresses
    """

    with settings(warn_only=True):
        reset_bitcoind()
        add_peers()
        return get_addresses()

def is_alliance(my_address):

    with settings(warn_only=False):
        result = cli("getmemberlist")
        member_list = json.loads(result)['member_list']

        return my_address in member_list

def wait_for_tx_confirmed(txid, flag_maturity=False, num_trial=20):
    """ Keep pooling bitcoind to get tx's confirmations. """

    with settings(warn_only=False):
        for i in xrange(num_trial):
            result = cli("getrawtransaction", txid, 1)
            result = json.loads(result)
            keys = map(str, result.keys())
            if 'confirmations' in keys:
                if not flag_maturity:
                    return True
                else:
                    if int(result['confirmations']) >= MATURITY:
                        return True
            sleep(1)

def wait_to_be_alliance(my_address, num_trial=10000):

    with settings(warn_only=False):
        for i in xrange(num_trial):
            if is_alliance(my_address):
                return True
            sleep(1)
        return False

@parallel
@roles('alliance')
def set_alliance():
    """
        1. let the alliance head become an alliance.
        2. vote to the others alliance.
    """

    my_pos = env.roledefs['alliance'].index(env.host)
    my_address = addresses[env.host][0]

    # is alliance head, setgenerate to be alliance
    if my_pos == 0:
        result = cli("setgenerate", "true")

        sleep(5)

        if not is_alliance(my_address):
            raise AutoTestError('alliance head')

    wait_to_be_alliance(my_address)
    cli("setgenerate", "true")

    num_alliances = len(env.roledefs['alliance'])
    for i in range(my_pos + 1, num_alliances):
        result = cli("mint", 1, 0)
        wait_for_tx_confirmed(result, True)

        candidate_address = addresses[env.hosts[i]][0]
        result = cli("sendvotetoaddress", candidate_address)

        wait_to_be_alliance(candidate_address)

def random_choose_an_address():

    peer = random.choice(addresses.keys())
    address = random.choice(addresses[peer])
    return peer, address

def alliance_track():
    """
    """

    prob_send_license = 1
    if random.randint(1, prob_send_license) != 1:
        return

    result = cli("mint", 1, 0)

    wait_for_tx_confirmed(result, True)

    peer, address = random_choose_an_address()

    color = random.randint(1, NUM_COLORS)

    result = cli("sendlicensetoaddress", address, color)

    wait_for_tx_confirmed(result)


def activate_addresses(color):

    NUM_ALL_ADDRESSES = len(env.hosts) * NUM_ADDRESSES

    for i in xrange(NUM_ALL_ADDRESSES * 2):
        result = cli("mint", 1, color)

    wait_for_tx_confirmed(result, True)

    for host, addr_list in addresses.items():
        # activate others' addresses first, in case of dependency
        # e.g. i mint to my_addr1, i send to my_addr2,
        # then send to others_addr1, this incurs error "addr not record
        # in blockchain"
        if host == env.host:
            continue
        for addr in addr_list:
            result = cli("sendtoaddress", addr, 1, color)
    # At last, activate our own addresses
    for addr in addresses[env.host]:
        result = cli("sendtoaddress", addr, 1, color)


    wait_for_tx_confirmed(result)

def check_license():

    result = cli("getlicenseinfo")
    result = json.loads(result)
    all_license = result.keys()

    for i in all_license:
        color = int(i)
        if env.host not in licenses.keys():
            licenses[env.host] = []
        if color not in licenses[env.host]:
            licenses[env.host].append(color)
            activate_addresses(color)

def issuer_track():

    check_license()

    if env.host not in licenses.keys():
        return

    my_licenses = licenses[env.host]

    for color in my_licenses:
        result = cli("mint", MINT_AMOUNT, color)
    wait_for_tx_confirmed(result, True)

def normal_track():

    result = cli("getbalance")
    balance = json.loads(result)

    peer, address = random_choose_an_address()
    color, money = random.choice(balance.items())
    color = int(color)
    money = int(money)
    money_out = money / 2
    result = cli("sendtoaddress", address, money_out, color)
    wait_for_tx_confirmed(result)

@parallel
def running():

    with settings(warn_only=False):
        my_address = addresses[env.host][0]
        if is_alliance(my_address):
            alliance_track()
        issuer_track()
        normal_track()

def testing():
    return env.host

def test():
    return testing()

if __name__ == '__main__':

    with hide():
        addresses = execute(setup_connections)
        execute(set_alliance)
        execute(running)