#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# author    :   kevin
# date      :   20150217
# purpose   :   very simple test for diqi

import inspect
import json
import random
import sys
import time

from os.path import expanduser
from subprocess import Popen, PIPE, STDOUT, call

from peer_addresses import peer_addresses

EXIT_FAILURE = 1

RPC_SUCCESS = 0
RPC_ERROR_INVALID_COLOR = 3
RPC_ERROR_WALLET = 4

UINT32_MAX = 2 ** 32 - 1
UINT32_MIN = 0
MINT_AMOUNT = 1000
NUM_COLOR = 100
SLEEP_TIME = 15
MATURITY = 11

def error(*args):

    sys.stderr.write(' '.join(map(str, args)) + '\n')

def rpc_calls(*args, **kwargs):
    """ Simply using shell calls to communicate with bitcoind.

        if p.returncode == 0:
            shell calls success, we should read from p.stdout.
        else p.returncode != 0:
            if p.returncode == 1:
                should be "couldn't connect to server" or something else.
            else:
                check for gcoin/src/rpcprotocol.h
    """

    args = [str(i) for i in args]
    p = Popen(["bitcoin-cli", "-gcoin"] + args, stdout=PIPE, stdin=PIPE,
             stderr=PIPE)
    out = p.communicate(input = "")

    if p.returncode == 0:
        return p.returncode, out[0].replace("\n", "")
    else:
        return p.returncode, out[1].replace("\n", "")

class EdgeTest(object):
    """Edge Testing"""

    license = []

    def import_wallet_address(self):

        (code, out) = rpc_calls("listwalletaddress")
        self.wallet_address = json.loads(out)
        print "%s : done" % (inspect.stack()[0][3],)

    def reset_bitcoind(self):

        return_code = call(["killall", "-9", "bitcoind"])

        time.sleep(3)

        return_code = call(["rm", "-rf", expanduser("~") + "/.bitcoin/gcoin"])
        return_code = call(["bitcoind", "-gcoin", "-daemon"])
        if return_code == 0:
            print "Resetting bitcoind...done"
            return True
        else:
            return False

    def reset_and_be_alliance(self, num_trial=10):

        if not self.reset_bitcoind():
            error("Error : reset bitcoind failed")
            return False

        count = 0
        while count < num_trial:
            (code, out) = rpc_calls("setgenerate", "true")
            if code == RPC_SUCCESS:
                return True

            time.sleep(2)
            count += 1

        return False

    def have_license(self, color):

        (code, out) = rpc_calls("getlicenseinfo")
        out = json.loads(out)
        all_license = out.keys()
        licenses = map(int, all_license)

        return True if color in licenses else False

    def minting_without_license(self):
        """ edge test 1-2 """

        flag_complete = False

        self.reset_and_be_alliance()
        self.import_wallet_address()

        # fetch licenses
        (code, out) = rpc_calls("getlicenseinfo")
        out = json.loads(out)
        all_license = out.keys()

        # find a color whose license is not belonged to us
        licenses = map(int, all_license)
        color = 1
        while True:
            if color not in licenses:
                break
            color += 1

        (code, out) = rpc_calls("mint", MINT_AMOUNT, color)

        if code == RPC_SUCCESS:
            flag_complete = False
        elif code == RPC_ERROR_WALLET:
            flag_complete = True
        else:
            error("Error :", "something goes wrong!", out)
            sys.exit(EXIT_FAILURE)

        return flag_complete

    def is_alliance(self):

        (code, out) = rpc_calls("getmemberlist")
        out = json.loads(out)
        for i in out[u'member_list']:
            if i == str(self.wallet_address[0]):
                return True
        return False

    def wait_for_tx_confirmation(self, txid, flag_maturity=False,
                                 num_trial=20):
        """ Keep pooling bitcoind to get tx's confirmations. """

        count = 0
        while count < num_trial:
            (code, out) = rpc_calls("getrawtransaction", txid, 1)
            out = json.loads(out)
            keys = map(str, out.keys())
            if 'confirmations' in keys:
                if not flag_maturity:
                    return True
                else:
                    if int(out['confirmations']) >= MATURITY:
                        return True
            count += 1
            time.sleep(1)

        return False

    def get_one_zeroes(self, number):

        for i in xrange(number):
            code, out = rpc_calls("mint", 1, 0)
            if code != RPC_SUCCESS:
                error("Error :", "mint 1 0 failed", out)
                sys.exit(EXIT_FAILURE)

        flag_mint_confirmed = self.wait_for_tx_confirmation(out, True)
        if flag_mint_confirmed != True:
            error("Error :", "mint 1 0 not confirmed")
            sys.exit(EXIT_FAILURE)

    def get_license_and_mint(self, address, amount, color):

        self.get_one_zeroes(1)

        code, out = rpc_calls("sendlicensetoaddress", address, color)
        if code != RPC_SUCCESS:
            error("Error :", "sendlicensetoaddress failed1", out)
            sys.exit(EXIT_FAILURE)
        flag_license_confirmed = self.wait_for_tx_confirmation(out)
        if flag_license_confirmed != True:
            error("Error :", "license not confirmed")
            sys.exit(EXIT_FAILURE)

        code, out = rpc_calls("mint", amount, color)
        if code != RPC_SUCCESS:
            error("Error :", "mint {0} {1} failed".format(amount, color), out)
            sys.exit(EXIT_FAILURE)
        flag_mint_confirmed = self.wait_for_tx_confirmation(out, True)
        if flag_mint_confirmed != True:
            error("Error :", "mint {0} {1} not confirmed".format(amount,
                                                                 color))
            sys.exit(EXIT_FAILURE)

    def color_test(self, color):
        """ Return if the license transaction is valid

            #Return value
                True,  if color is ok.
                False, if color is not ok.
        """

        (code, txid) = rpc_calls("mint", 1, 0)

        flag_mint_confirmed = self.wait_for_tx_confirmation(txid, True)
        if flag_mint_confirmed != True:
            error("Error :", "mint 1 0 not confirmed")
            sys.exit(EXIT_FAILURE)

        (code, txid) = rpc_calls("sendlicensetoaddress",
                                 self.wallet_address[0], color)
        if code == RPC_ERROR_INVALID_COLOR or code == RPC_ERROR_WALLET:
            return False
        elif code != RPC_ERROR_INVALID_COLOR and code != RPC_SUCCESS:
            error("Error :", "sendlicensetoaddress failed2", txid)
            sys.exit(EXIT_FAILURE)

#        print "Waiting for license tx: {0} to be confirmed...".format(txid)
        flag_license_confirmed = self.wait_for_tx_confirmation(txid)
        if flag_license_confirmed != True:
            error("Error :", "license not confirmed")
            sys.exit(EXIT_FAILURE)

        return True

    def usable_color_test(self):
        """ edge test 3-1 """

        flag_complete = True
        testing_color = [UINT32_MIN - 1, UINT32_MIN, UINT32_MIN + 1,
                         UINT32_MAX - 1, UINT32_MAX, UINT32_MAX + 1]
        testing_answer = [False, False, True, True, True, False]

        self.reset_and_be_alliance()
        self.import_wallet_address()

        for i in xrange(len(testing_color)):
            result = self.color_test(testing_color[i])
            if result != testing_answer[i]:
                print "color %d failed, result=%r answer=%r" % (
                       testing_color[i], result, testing_answer[i])
                flag_complete = False

        return flag_complete

    def mint_test(self, amount, color):

        if self.color_test(color) != True:
            error("Error :", "something wrong in creating license")
            sys.exit(EXIT_FAILURE)

        code, out = rpc_calls("mint", amount, color)
        if code == RPC_SUCCESS:
            result = True
        elif code == RPC_ERROR_WALLET:
            result = False
        else:
            error("Error: ", "mint not confirmed")
            sys.exit(EXIT_FAILURE)
        return result

    def mint_amount_test(self):
        """ edge test 3-2

            #Caution
            1. Mint amount should be integer
            2. Max amount is 10**10
            3. Using multiple colors to prevent from overflow of coins of
               one single color

            #Return Value
                True    :   pass
                False   :   fail
        """

        MAX_AMOUNT = 10 ** 10
        flag_complete = True
        testing_amount = [-1, 0, 1, MAX_AMOUNT - 1, MAX_AMOUNT, MAX_AMOUNT + 1]
        testing_color = [1, 2, 3, 4, 5, 6]
        testing_answer = [False, False, True, True, True, False]

        self.reset_and_be_alliance()
        self.import_wallet_address()

        # preparing for licenses
        for i in xrange(len(testing_amount)):
            result = self.mint_test(testing_amount[i], testing_color[i])
            if result != testing_answer[i]:
                print "Error :", "testing_amount %d failed" % testing_amount[i]
                flag_complete = False
        return flag_complete

    def nonmember_transactions(self):
        """ edge test 1-3

            #Target
                Test if error occurs when an nonmember address receive coins.

            #Figures
                wallet_address[0] is a member, wallet_address[1] is a
                nonmember.

            #Return Value
                True    :   pass
                False   :   fail
        """

        TEST_COLOR = 123

        self.reset_and_be_alliance()
        self.import_wallet_address()
        self.get_license_and_mint(self.wallet_address[0], 1, TEST_COLOR)

        # activate wallet_address[1]
        code, out = rpc_calls("sendtoaddress", self.wallet_address[1], 1, TEST_COLOR)
        if code != RPC_SUCCESS:
            error("Error :", "sendtoaddress failed", out)
            sys.exit(EXIT_FAILURE)
        flag_tx_confirmed = self.wait_for_tx_confirmation(out)
        if flag_tx_confirmed != True:
            error("Error :", "sendtoaddress tx not confirmed")
            sys.exit(EXIT_FAILURE)

        # transfer money to a nonmember, i.e. wallet_address[2]
        code, out = rpc_calls("sendtoaddress", self.wallet_address[2], 1, TEST_COLOR)
        if code != RPC_ERROR_WALLET:
            return False
        return True

    def coins_transfer_test(self):
        """ edge test 3-4

            #Figure
                By default NUM_ADDRESSES = 3,
                wallet_address[1], wallet_address[2], wallet_address[3]

            #course
                1. Everyone get some coins.
                2. Randomly choose 2 addresses from the given addresses,
                   and sendfrom the one to the other. This operation will be
                   repeated for NUM_TESTS times.
                3. Count the balance of NUM_ADDRESSES addresses, and call
                   getaddressbalance to identify if the numbers are correct
                   or not.

            #Return Value
                True    :   pass
                False   :   fail
        """

        NUM_TESTS = 20
        NUM_ADDRESSES = 3
        TEST_COLOR = 123
        BASE = 1
        TOTAL_COINS = 10000 * NUM_ADDRESSES * BASE

        flag_complete = True
        accumulate_value = [0] * (NUM_ADDRESSES + 1)


        self.reset_and_be_alliance()
        self.import_wallet_address()
        self.get_license_and_mint(self.wallet_address[0], TOTAL_COINS / BASE,
                                  TEST_COLOR)

        # phase 1
        for i in xrange(1, NUM_ADDRESSES + 1):
            amount = TOTAL_COINS / NUM_ADDRESSES

            code, out = rpc_calls("sendfrom", self.wallet_address[0],
                                  self.wallet_address[i], amount / BASE, TEST_COLOR)
            if code != RPC_SUCCESS:
                error("Error :", "sendfrom failed", out)
                sys.exit(EXIT_FAILURE)
            if self.wait_for_tx_confirmation(out) != True:
                error("Error :", "sendfrom tx not confirmed")
                sys.exit(EXIT_FAILURE)

            accumulate_value[0] -= amount
            accumulate_value[i] += amount

        # phase 2
        for i in xrange(NUM_TESTS):
            sender, receiver = random.sample(range(1, NUM_ADDRESSES + 1), 2)
            # TODO: make random.uniform case works!
            amount = random.randint(BASE, accumulate_value[sender])
            code, out = rpc_calls("sendfrom", self.wallet_address[sender],
                                  self.wallet_address[receiver], amount / float(BASE),
                                  TEST_COLOR)
            if code != RPC_SUCCESS:
                error("Error :", "sendfrom failed", out)
                sys.exit(EXIT_FAILURE)
            if self.wait_for_tx_confirmation(out) != True:
                error("Error :", "sendfrom tx not confirmed")
                sys.exit(EXIT_FAILURE)

            accumulate_value[sender] -= amount
            accumulate_value[receiver] += amount

        # phase 3
        for i in xrange(1, NUM_ADDRESSES + 1):
            code, out = rpc_calls("getaddressbalance", self.wallet_address[i])
            out = json.loads(out)
            if code != RPC_SUCCESS:
                error("Error :", "getaddressbalance failed", out)
                sys.exit(EXIT_FAILURE)

            address_balance = float(out[str(TEST_COLOR)])
            address_balance = address_balance * BASE
            if address_balance != accumulate_value[i]:
                print "%s balance not consistent, rpc: %r, accu: %r" % (
                      self.wallet_address[i], address_balance,
                      accumulate_value[i])
                flag_complete = False

        return flag_complete

    def __init__(self):

        print self.minting_without_license()
        print self.mint_amount_test()
        print self.usable_color_test()
        print self.coins_transfer_test()

if __name__ == "__main__":
    t = EdgeTest()
