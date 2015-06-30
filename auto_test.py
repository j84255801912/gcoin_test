#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import random
import sys
import threading

import ConfigParser

from time import sleep, time

from fabric.api import *
from fabric.context_managers import hide
from fabric.tasks import execute
from fabric.operations import get

MATURITY = 11 # num of blocks that the coinbase tx need to become spendable
NUM_ADDRESSES = 10 # num of address per host
PORT = 55888 # the port the hosts listen to
NUM_COLORS = 1000 # num of color you want to use
MINT_AMOUNT = 100 # the mint amount per mint transaction
SAFE_SLEEP = True # sleep for a short time after each transaction conducted
HIGH_TPS = False # boost the tps
RESET_BLOCKCHAIN = True

addresses = {}
licenses = {}

class AutoTestError(Exception):

    def __init__(self, message):

        if env.host is not None:
            message = str(env.host) + ' ' + message
        super(AutoTestError, self).__init__(message)


class RedirectStreams(object):

    def __init__(self, stdout=None, stderr=None):

        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):

        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):

        self._stdout.flush()
        self._stderr.flush()
        sys.stdout, sys.stderr = self.old_stdout, self.old_stderr


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

@parallel
def reset_bitcoind():

    with settings(warn_only=True):
        run("killall bitcoind -9")

        # XXX : magic
        sleep(3)

        run("rm -rf $HOME/.bitcoin/gcoin")

        # TODO: if bitcoind has problem, e.g. Error: OpenSSL lack support for
        # ECDSA, we should handle error?
        result = run("bitcoind -gcoin -daemon -port={0} ".format(PORT) +
                     "-logip -debug")
        if result.failed:
            AutoTestError("bitcoind launch failed")

def get_host_from_envhost(host):

    at_pos = host.find('@')
    if at_pos != -1:
        host = host[at_pos + 1:]
    return host

def add_peers():

    for host in env.hosts:
        # add peers except for myself
        if host != env.host:
            host = get_host_from_envhost(host)
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

        confirm_bitcoind_functioning()
        add_peers()
        return get_addresses()

def is_alliance(my_address):

    result = cli("getmemberlist")
    member_list = json.loads(result)['member_list']

    return my_address in member_list

def sleep_for_broadcast(func):

    def decorating(*args, **kwargs):
        func(*args, **kwargs)
        sleep(15 if 'flag_maturity' in kwargs.keys() and
                 kwargs['flag_maturity'] == True and SAFE_SLEEP
              else 3)

    return decorating

@sleep_for_broadcast
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
        sleep(2)
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
    wait_for_tx_confirmed(result, flag_maturity=True)

def let_others_be_alliance(my_pos, my_address):

    num_alliances = len(env.roledefs['alliance'])

    get_mint_funds(0, num_alliances * 2)

    for i in xrange(my_pos + 1, num_alliances):
        candidate_host = env.roledefs['alliance'][i]
        candidate_address = addresses[candidate_host][0]
        result = cli("sendvotetoaddress", candidate_address)

        wait_to_be_alliance(candidate_address)

@roles('alliance')
@parallel
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

    # XXX for safety, not allowing too much license generated
    if count > 1000:
        return False

    # this means 1/prob_send_license probability that gives out a license
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

def random_send_random_license():

    peer, address = random_choose_an_address()
    color = random.randint(1, NUM_COLORS)

    if possible_license_transfer(color):
        return

    result = cli("sendlicensetoaddress", address, color)
#    if result.succeeded:
#        wait_for_tx_confirmed(result)

def alliance_track(count):
    """
    """

    if not execute_or_not(count):
        return

    result = cli("mint", 1, 0)
    if result.failed:
        return
    wait_for_tx_confirmed(result, flag_maturity=True)

    random_send_random_license()

def get_my_license_address(color):

    result = cli("getlicenseinfo")
    result = json.loads(result)
    return result[str(color)]["address"]

def send_from_to_all_addresses(from_address, color, num_trial=20):

    for host, addr_list in addresses.items():
        for addr in addr_list:
            result = cli("sendfrom", from_address, addr, 1, color)
            # XXX here is to ensure that all address is activated!
            for i in xrange(num_trial):
                if result.succeeded:
                    break
                result = cli("sendfrom", from_address, addr, 1, color)
                sleep(1)

#    if result.succeeded:
#        wait_for_tx_confirmed(result)

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
            # XXX if run without reset bitcoind, we waste a lot of time here.
            if SAFE_SLEEP and not RESET_BLOCKCHAIN:
                sleep(20)

            activate_addresses(color)

def mint_all_i_can_mint(my_licenses):

    for color in my_licenses:
        iterations = 1000 if HIGH_TPS else 1
        result = run("for i in $(seq 1 %d);" % iterations +
                     "do " +
                     "bitcoin-cli -gcoin mint %d %d;" % (MINT_AMOUNT, color) +
                     "done"
                 )
#    if result.succeeded:
#        wait_for_tx_confirmed(result, flag_maturity=True)

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
    money_out = money / 5
    if money_out == 0:
        return
    result = cli("sendtoaddress", address, money_out, color)
#    if result.succeeded:
#        wait_for_tx_confirmed(result)

def normal_track():

    for i in xrange(20 if HIGH_TPS else 1):
        result = cli("getbalance")
        balance = json.loads(result)
        # if no balance then return
        if balance == {} or balance.keys() == ['0']:
            return

        random_send_money(balance)

@parallel
def running():

    count = 0
    while True:
        my_address = addresses[env.host][0]
        if is_alliance(my_address):
            alliance_track(count)
        issuer_track()
        normal_track()
        count += 1

        # sleep for yielding cpu
        sleep(1)

@parallel
def get_debug_log_error():

    command = 'egrep \'(error|ERROR)\' ~/.bitcoin/gcoin/debug_* | '
    command += 'awk \'{$1="";$2=""; print}\' | sort | uniq'
    result = run(command)
    return result

def see_all_debug_error():

    result = execute(get_debug_log_error)
    for key, value in result.items():
        print
        print key
        print "======================================"
        print value

@roles('monitor')
def print_tps(output_file):

    sleep(1)

    sleep_time = 10

    start_time = time()
    result = cli('getblockcount')
    last_block_height = int(result)

    cumulate_tx_count = 0
    count = 0

    while 1:
        sleep(sleep_time)
        elapsed_time = int(time() - start_time)

        result = cli('getblockcount')
        now_block_height = int(result)

        recent_cumulate_tx_count = 0
        while now_block_height >= last_block_height:
            block_hash = cli('getblockhash', last_block_height)
            block_data = cli('getblock', block_hash)
            block_data = json.loads(block_data)
            recent_cumulate_tx_count += len(block_data[u'tx'])
            last_block_height += 1
        last_block_height = now_block_height

        cumulate_tx_count += recent_cumulate_tx_count

        result = cli('getrawmempool')
        mempool_tx = json.loads(result)
        mempool_tx_count = len(mempool_tx)

        output_file.write("\n%s\n=========================\n" % env.host)
        formatter = "tps\tlast_{}_sec_tps\tblocks\tmempool_txs\n"
        output_file.write(formatter.format(sleep_time))
        formatter = "{}\t{}\t{}\t{}\n"
        output_file.write(formatter.format(
                    round(cumulate_tx_count / float(elapsed_time), 2),
                    round(recent_cumulate_tx_count / float(sleep_time), 2),
                    now_block_height,
                    mempool_tx_count))
        last_block_height = now_block_height

def setup_monitor(output_file):

    execute(print_tps, output_file)

def get_debug_log(log_dir):

    return get(remote_path="/home/kevin/.bitcoin/gcoin/debug*.log", local_path='.')

@parallel
def test(ha):

    result = run('for i in $(seq 1 10); do echo {}; done'.format(ha))
    print result
    #result = run('echo $RANDOM')
    '''
    f1 = open('out', 'a')
    f2 = open('err', 'a')
    result = run('ddddd', stdout=f1, stderr=f2)
    '''

def parsing_hosts():

    c = ConfigParser.ConfigParser(allow_no_value=True)
    c.readfp(open('test.conf'))
    if not(set(['user', 'password', 'alliance', 'others', 'monitor']) <=
           set(c.sections())):
        raise AutoTestError("Config file: missing sections")

    env.user = c.items('user')[0][0]
    env.password = c.items('password')[0][0]

    env.roledefs['alliance'] = [i[0] for i in c.items('alliance')]
    env.roledefs['others'] = [i[0] for i in c.items('others')]
    env.roledefs['monitor'] = [i[0] for i in c.items('monitor')]
    env.hosts = list(set(env.roledefs['alliance'] + env.roledefs['others']))

def start_all_miner():

    cli('setgenerate', 'true', 1)

if __name__ == '__main__':

    parsing_hosts()

    #execute(test, 'shit')

    reset_blockchain = raw_input("reset block chain and connections?(y/n):[y] ")
    if reset_blockchain.find('n') != -1:
        RESET_BLOCKCHAIN = False
    mode = raw_input("High tps mode? (y/n):[n] ")
    if RESET_BLOCKCHAIN:
        safe_sleep = raw_input("Safe sleep? (y/n):[y] ")
    else:
        safe_sleep = 'n'

    multiple_color = raw_input("Mutiple colors? (y/n):[y] ")
    NUM_ADDRESSES = raw_input("Number of addresses for each node?:[50] ") or 50
    NUM_ADDRESSES = int(NUM_ADDRESSES)
    if mode.find('y') != -1:
        HIGH_TPS = True
    if safe_sleep.find('n') != -1:
        SAFE_SLEEP = False
    if multiple_color.find('n') != -1:
        NUM_COLORS = 1

    with settings(hide(), warn_only=True),\
        open('stdout', 'w' if RESET_BLOCKCHAIN else 'a') as stdout_file,\
        open('stderr', 'w' if RESET_BLOCKCHAIN else 'a') as stderr_file:

        if RESET_BLOCKCHAIN:
            print "Resetting bitcoind"
            with RedirectStreams(stdout=stdout_file, stderr=stderr_file):
                execute(reset_bitcoind)

        print "Setting up connections and get addresses..."
        with RedirectStreams(stdout=stdout_file, stderr=stderr_file):
            addresses = execute(setup_connections)
            if not RESET_BLOCKCHAIN:
                execute(start_all_miner)

        if RESET_BLOCKCHAIN:
            print "Setting up alliance..."
            with RedirectStreams(stdout=stdout_file, stderr=stderr_file):
                execute(set_alliance)

        if env.roledefs['monitor'] != []:
            t = threading.Thread(name="monitor thread", target=setup_monitor, args=(sys.stdout,))
            t.start()

        print "Start running auto test..."
        with RedirectStreams(stdout=stdout_file, stderr=stderr_file):
            execute(running)

