#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# author    :   kevin
# date      :   20150217
# purpose   :   very simple test for diqi

import inspect
import json
import os
import random
import sys
import time

from subprocess import Popen, PIPE, STDOUT, call

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

ERROR_HAVE_NO_LICENSE = "you don't have this license"
ERROR_LICENSE_NOT_GENERATED = "license of this color hasn't been generated yet"
ERROR_SERVER_CONNECTION = "couldn't connect to server"
ERROR_INVALID_COLOR = "Invalid color"
ERROR_MINT_OVER_MAXCOIN = "mint Value > MaxCoin"
ERROR_MINT_VALUE_NEGATIVE = "CommitTransaction() : Error: MINT Transaction \
not valid"
ERROR_MINT_VALUE_ZERO = "mint value should not be 0"
ERROR_COINS_TOO_MUCH = "coins of this color may overflow"
ERROR_TRANSACTION_REJECTED = "Error: The transaction was rejected! This might \
happen if some of the coins in your wallet were already spent, such as if \
you used a copy of wallet.dat and coins were spent in the copy but not \
marked as spent here."

def extract_error_message(out):

    index = out.find('{')
    if index == -1:
        return out[len('error:') + 1:]
    error_json = json.loads(out[index:])
    return error_json['message']

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
        message = extract_error_message(out[1].replace("\n", ""))
        return p.returncode, message

class EdgeTest(object):
    """Edge Testing"""

    license = []

    def import_wallet_address(self):

        code, out = rpc_calls("listwalletaddress", "-p")
        self.wallet_address = json.loads(out)
#        print "%s...done" % (inspect.stack()[0][3],)

    def reset_bitcoind(self):

        # note: stdout&stderr is redirected to /dev/null,
        # which makes debug more difficult
        with open(os.devnull, 'wb') as dev_null:
            return_code = call(["killall", "-9", "bitcoind"],
                               stdout=dev_null, stderr=dev_null)

            time.sleep(3)

            return_code = call(["rm", "-rf",
                                os.path.expanduser("~") + "/.bitcoin/gcoin"],
                                stdout=dev_null, stderr=dev_null)
            return_code = call(["bitcoind", "-gcoin", "-daemon"],
                                stdout=dev_null, stderr=dev_null)
            if return_code == 0:
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

    def mint_without_license(self):
        """ edge test 1-2 """

        flag_complete = False

        case = [None]
        answer = [None]
        pass_or_not = [True]

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

        code, out = rpc_calls("mint", MINT_AMOUNT, color)

        if code == RPC_SUCCESS:
            pass_or_not[0] = False
        else:
            if out == ERROR_HAVE_NO_LICENSE or out == ERROR_LICENSE_NOT_GENERATED:
                pass_or_not[0] = True
            else:
                error("Error: ", "something wrong")
                sys.exit(EXIT_FAILURE)

        return pass_or_not

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

        code, txid = rpc_calls("mint", 1, 0)

        flag_mint_confirmed = self.wait_for_tx_confirmation(txid, True)
        if flag_mint_confirmed != True:
            error("Error :", "mint 1 0 not confirmed")
            sys.exit(EXIT_FAILURE)

        code, txid = rpc_calls("sendlicensetoaddress",
                                 self.wallet_address[0], color)
        if code != RPC_SUCCESS:
            if txid == ERROR_INVALID_COLOR:
                return False
            error("Error :", "sendlicensetoaddress failed2", txid)
            sys.exit(EXIT_FAILURE)

        flag_license_confirmed = self.wait_for_tx_confirmation(txid)
        if flag_license_confirmed != True:
            error("Error :", "license not confirmed")
            sys.exit(EXIT_FAILURE)

        return True

    def usable_color_test(self):
        """ edge test 3-1 """

        flag_complete = True

        case = [UINT32_MIN - 1, UINT32_MIN, UINT32_MIN + 1,
                         UINT32_MAX - 1, UINT32_MAX, UINT32_MAX + 1]
        answer = [False, False, True, True, True, False]
        pass_or_not = [True] * len(case)

        self.reset_and_be_alliance()
        self.import_wallet_address()

        for i in xrange(len(case)):
            result = self.color_test(case[i])
            if result != answer[i]:
                print "color %d failed, result=%r answer=%r" % (
                       case[i], result, answer[i])
                pass_or_not[i] = False

        return pass_or_not

    def mint_test(self, amount, color):

        if self.color_test(color) != True:
            error("Error :", "something wrong in creating license")
            sys.exit(EXIT_FAILURE)

        code, out = rpc_calls("mint", amount, color)

        if code == RPC_SUCCESS:
            return True
        if out == ERROR_MINT_OVER_MAXCOIN or out == ERROR_MINT_VALUE_NEGATIVE\
           or out == ERROR_MINT_VALUE_ZERO:
            return False
        error("Error: ", "mint error", out)
        sys.exit(EXIT_FAILURE)

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
        testing_color = [1, 2, 3, 4, 5, 6]

        case = [-1, 0, 1, MAX_AMOUNT - 1, MAX_AMOUNT, MAX_AMOUNT + 1]
        answer = [False, False, True, True, True, False]
        pass_or_not = [True] * len(case)

        self.reset_and_be_alliance()
        self.import_wallet_address()

        # preparing for licenses
        for i in xrange(len(case)):
            result = self.mint_test(case[i], testing_color[i])
            if result != answer[i]:
                pass_or_not[i] = False
        return pass_or_not

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

        case = [None]
        answer = [None]
        pass_or_not = [True]

        self.reset_and_be_alliance()
        self.import_wallet_address()
        self.get_license_and_mint(self.wallet_address[0], 1, TEST_COLOR)

        # activate wallet_address[1]
        code, out = rpc_calls("sendfrom", self.wallet_address[0],
                              self.wallet_address[1], 1, TEST_COLOR)
        if code != RPC_SUCCESS:
            error("Error :", "sendfrom failed", out)
            sys.exit(EXIT_FAILURE)
        flag_tx_confirmed = self.wait_for_tx_confirmation(out)
        if flag_tx_confirmed != True:
            error("Error :", "sendfrom tx not confirmed")
            sys.exit(EXIT_FAILURE)

        # transfer money to a nonmember, i.e. wallet_address[2]
        code, out = rpc_calls("sendfrom", self.wallet_address[1],
                              self.wallet_address[2], 1, TEST_COLOR)
        if code == RPC_ERROR_WALLET and out == ERROR_TRANSACTION_REJECTED:
            pass_or_not[0] = True
        else:
            pass_or_not[0] = False

        return pass_or_not

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

        # params
        NUM_TESTS = 20
        NUM_ADDRESSES = 3
        TEST_COLOR = 123

        case = [None]
        answer = [None]
        pass_or_not = [True]

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
            amount = random.randint(BASE, accumulate_value[sender] * BASE)
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
                pass_or_not[0] = False

        return pass_or_not

    def __init__(self):
        test_name = [
                     'mint_without_license',
                     'mint_amount_test',
                     'usable_color_test',
                     'nonmember_transactions',
                     'coins_transfer_test'
                    ]

        result = []
        for i in xrange(len(test_name)):
            func_name = test_name[i]
            func = getattr(self, func_name)
            print "{}/{} {}...".format(i+1, len(test_name), func_name)
            result.append(func())

        print "\n\nResult\n============================="
        for i in xrange(len(test_name)):
            print test_name[i] + '...',
            if False not in result[i]:
                print "Pass!"
                continue
            print "Fail in case:",
            print ' '.join([str(j) for j in xrange(len(result[i]))
                                   if result[i][j] != True])

if __name__ == "__main__":
    t = EdgeTest()
