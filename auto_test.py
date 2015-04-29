#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import random

from time import sleep

from fabric.api import *
from fabric.context_managers import hide
from fabric.tasks import execute

from setting import user, password

env.hosts = ["127.0.0.1", "140.112.29.201", "core1.diqi.us", "core2.diqi.us", "core3.diqi.us", "core4.diqi.us"]
#env.hosts = ["127.0.0.1"]
env.roledefs = {
    "alliance":   env.hosts,
}

env.user = user
env.password = password


addresses = {}
licenses = {}

NUM_ADDRESSES = 10
PORT = 55777
MATURITY = 11
NUM_COLORS = 1000
MINT_AMOUNT = 1000

class AutoTestError(Exception):

    def __init__(self, message):

        super(AutoTestError, self).__init__(str(env.host) + ' ' + str(message))

def cli(*args, **kwargs):

    result = run("bitcoin-cli -gcoin " + ' '.join(map(str, args)))
    if result.failed and result == "error: couldn't connect to server":
        raise AutoTestError("bitcoind crashed")
    return result

def cli_can_fail(*args, **kwargs):

    return run("bitcoin-cli -gcoin " + ' '.join(map(str, args)))

def confirm_bitcoind_functioning(num_trial=20):

    for i in xrange(num_trial):
        result = cli_can_fail("getinfo")
        if result.succeeded:
            return result
        sleep(1)
    raise AutoTestError('bitcoind not functioning')

def reset_bitcoind():

    run("killall bitcoind -9")

    # XXX : magic
    sleep(3)

    run("rm -rf $HOME/.bitcoin/gcoin")

    # TODO: if bitcoind has problem, e.g. Error: OpenSSL lack support for
    # ECDSA, we should handle error?
    result = run("bitcoind -gcoin -daemon -port={} -logip -debug".format(PORT))
    if result.failed:
        AutoTestError("bitcoind launch failed")

    confirm_bitcoind_functioning()

def add_peers():

    for host in env.hosts:
        # add peers except for myself
        if host != env.host:
            cli("addnode", "{}:{}".format(host, PORT), 'add')
            cli("addnode", "{}:{}".format(host, PORT), 'onetry')

def get_addresses(num_trial=100):

    for i in xrange(num_trial):
        result = cli("listwalletaddress", "-p", NUM_ADDRESSES)
        if result.succeeded:
            result = json.loads(result)
            return map(str, result)
        sleep(1)
    raise AutoTestError("get address error")

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

    result = cli("getmemberlist")
    member_list = json.loads(result)['member_list']

    return my_address in member_list

def wait_for_tx_confirmed(txid, flag_maturity=False):
    """ Keep pooling bitcoind to get tx's confirmations. """

    if txid.failed:
        return
    if not flag_maturity:
        num_trial = 15 * 10
    else:
        num_trial = 15 * MATURITY * 10

    for i in xrange(num_trial):
        result = cli("getrawtransaction", txid, 1)
        result = json.loads(result)
        keys = map(str, result.keys())
        if 'confirmations' in keys:
            if not flag_maturity:
                return
            else:
                if int(result['confirmations']) >= MATURITY:
                    return
        sleep(1)
    raise AutoTestError('transaction not confirmed')

def wait_to_be_alliance(my_address, num_trial=240):

    for i in xrange(num_trial):
        if is_alliance(my_address):
            return
        sleep(1)
    raise AutoTestError('alliance')

def let_me_be_alliance(my_pos, my_address):

    # is alliance head, setgenerate to be alliance
    if my_pos == 0:
        result = cli("setgenerate", "true")
        if result.failed or result == 'false':
            raise AutoTestError('being alliance failed')
        wait_to_be_alliance(my_address, num_trial=60)

        #XXX sleep for a long time to ensure that everyone acknowledge
        #    the first alliance
        sleep(10)
    else:
        wait_to_be_alliance(my_address)
        #XXX magic
        sleep(10)
        result = cli("setgenerate", "true")
        if result.failed or result == 'false':
            raise AutoTestError('being alliance failed')

def get_mint_funds(color, number):

    for i in xrange(number):
        result = cli("mint", 1, color)
    if result.succeeded:
        wait_for_tx_confirmed(result, True)

def let_others_be_alliance(my_pos, my_address):

    num_alliances = len(env.roledefs['alliance'])

    get_mint_funds(0, num_alliances * 2)

    for i in xrange(my_pos + 1, num_alliances):
        candidate_address = addresses[env.hosts[i]][0]
        result = cli("sendvotetoaddress", candidate_address)

        wait_to_be_alliance(candidate_address)

@parallel
@roles('alliance')
def set_alliance():
    """
        1. let the alliance head become an alliance.
        2. vote to the others alliance.
    """

    my_pos = env.roledefs['alliance'].index(env.host)
    my_address = addresses[env.host][0]

    let_me_be_alliance(my_pos, my_address)
    let_others_be_alliance(my_pos, my_address)

def random_choose_an_address():

    peer = random.choice(addresses.keys())
    address = random.choice(addresses[peer])
    return peer, address

def execute_or_not(count):

    # the first time we allow a license generated instantly.
    if count == 0 and env.host == env.roledefs['alliance'][0]:
        return True

    # this means 1/40 probability that gives out a license
    prob_send_license = 40
    if random.randint(1, prob_send_license) != 1:
        return False
    return True

def get_all_license():

    result = cli("getlicenseinfo")
    result = json.loads(result)
    all_license = map(int, result.keys())
    return all_license

def possible_license_transfer(color):
    """ To prevent from license transfer, which may cause error.
    """

    all_license = get_all_license()
    if color in all_license:
        return True
    return False

def random_send_an_random_license():

    peer, address = random_choose_an_address()
    color = random.randint(1, NUM_COLORS)

    if possible_license_transfer(color):
        return

    result = cli("sendlicensetoaddress", address, color)
    if result.succeeded:
        wait_for_tx_confirmed(result)

def alliance_track(count):
    """
    """

    if not execute_or_not(count):
        return

    result = cli("mint", 1, 0)
    if result.failed:
        return
    wait_for_tx_confirmed(result, True)

    random_send_an_random_license()

def get_my_license_address(color):

    result = cli("getlicenseinfo")
    result = json.loads(result)
    return result[str(color)]["address"]

def send_from_to_all_addresses(from_address, color, num_trial=10):

    for host, addr_list in addresses.items():
        for addr in addr_list:
            result = cli("sendfrom", from_address, addr, 1, color)
            # XXX here is to ensure that all address is activated!
            for i in xrange(num_trial):
                if result.succeeded:
                    break
                result = cli("sendfrom", from_address, addr, 1, color)

    if result.succeeded:
        wait_for_tx_confirmed(result)


def activate_addresses(color):

    NUM_ALL_ADDRESSES = len(env.hosts) * NUM_ADDRESSES

    get_mint_funds(color, NUM_ALL_ADDRESSES * 2)

    my_license_address = get_my_license_address(color)

    send_from_to_all_addresses(my_license_address, color)

def check_license():
    """ check my all licenses and activate addresses if a new license arrives
    """

    all_license = get_all_license()
    for i in all_license:
        color = int(i)
        if env.host not in licenses.keys():
            licenses[env.host] = []
        if color not in licenses[env.host]:
            licenses[env.host].append(color)
            # XXX
            sleep(15)

            activate_addresses(color)

def mint_all_i_can_mint(my_licenses):

    for color in my_licenses:
        result = cli("mint", MINT_AMOUNT, color)
    if result.succeeded:
        wait_for_tx_confirmed(result, True)


def issuer_track():

    check_license()

    if env.host not in licenses.keys():
        return

    my_licenses = licenses[env.host]

    mint_all_i_can_mint(my_licenses)

def random_send_money(balance):

    peer, address = random_choose_an_address()
    color, money = random.choice(balance.items())

    color = int(color)
    money = int(money)
    if color == 0:
        return
    money_out = money / 2
    if money_out == 0:
        return
    result = cli("sendtoaddress", address, money_out, color)
    if result.succeeded:
        wait_for_tx_confirmed(result)

def normal_track():

    result = cli("getbalance")
    balance = json.loads(result)
    # if no balance then return
    if balance == {}:
        return

    random_send_money(balance)

@parallel
def running():

    count = 0
    while True:
        print "======== {}th round ========".format(count + 1)
        my_address = addresses[env.host][0]
        if is_alliance(my_address):
            alliance_track(count)
        issuer_track()
        normal_track()
        count += 1

def testing():

    result = cli("getinfo")
    return result

def test():

    return testing()

@parallel
def test_now():

    i = 0
    i += 1
    print i

@parallel
def get_debug_log_error():

    result = run('egrep \'(error|ERROR)\' ~/.bitcoin/gcoin/debug_* | awk \'{$1="";$2=""; print}\' | sort | uniq')
    return result

def see_all_debug_error():

    result = execute(get_debug_log_error)
    for key, value in result.items():
        print
        print key
        print "======================================"
        print value


if __name__ == '__main__':

    with settings(hide(), warn_only=True):
        print "Setting up connections and get addresses..."
        addresses = execute(setup_connections)
        print "Setting up alliance..."
        execute(set_alliance)
        print "Start running auto test..."
        execute(running)
    '''
    see_all_debug_error()
    '''
