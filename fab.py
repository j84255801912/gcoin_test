#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from time import sleep

from fabric.api import *
from fabric.context_managers import hide
from fabric.tasks import execute

from setting import user, password

env.hosts = ["140.112.29.201", "127.0.0.1", "core1.diqi.us"]
env.roledefs = {
    "alliance":   env.hosts,
}

env.user = user
env.password = password


addresses = {}
NUM_ADDRESSES = 10
PORT = 55666
MATURITY = 11


class AutoTestError(Exception):

    def __init__(self, message):

        super(AutoTestError, self).__init__(message)

def cli(*args, **kwargs):
    return run("bitcoin-cli -gcoin " + ' '.join(map(str, args)))

def reset_bitcoind():

    run("killall -9 bitcoind")

    sleep(3)

    run("rm -rf $HOME/.bitcoin/gcoin")

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

    with settings(warn_only=True):
        result = cli("getmemberlist")
        member_list = json.loads(result)['member_list']

        return my_address in member_list

def wait_for_tx_confirmed(txid, flag_maturity=False, num_trial=20):
    """ Keep pooling bitcoind to get tx's confirmations. """

    with settings(warn_only=True):
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

    with settings(warn_only=True):
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
    cli("setgenerate true")

    num_alliances = len(env.roledefs['alliance'])
    for i in range(my_pos + 1, num_alliances):
        result = cli("mint", 1, 0)
        wait_for_tx_confirmed(result, True)

        candidate_address = addresses[env.hosts[i]][0]
        result = cli("sendvotetoaddress", candidate_address)

        wait_to_be_alliance(candidate_address)

if __name__ == '__main__':

    with hide('everything'):
        addresses = execute(setup_connections)
        execute(set_alliance)
