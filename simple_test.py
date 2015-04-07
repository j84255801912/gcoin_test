#!/usr/bin/python2.7
#
# author    :   kevin
# date      :   20150217
# purpose   :   very simple test for diqi

import inspect
import json
from os.path import expanduser
import random
import sys
import time

from subprocess import Popen, PIPE, STDOUT, call
from peer_addresses import peer_addresses

RPC_SUCCESS = 0
RPC_ERROR_INVALID_COLOR = 3
RPC_ERROR_WALLET = 4

UINT32_MAX = 2 ** 31 - 1
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

class Test(object):
    """Testing"""

    license = []

    def import_wallet_address(self):
        (code, out) = rpc_calls("listwalletaddress")
        self.wallet_address = json.loads(out)
        print "%s : done" % (inspect.stack()[0][3],)

    def import_peer_address(self):
        self.peer_address = peer_addresses
        print "%s : done" % (inspect.stack()[0][3],)

    def mint(self, amount, color):
        return rpc_calls("mint", amount, color)[1]

    def activate(self, color):
        for i in xrange(len(self.peer_address)):
            self.mint(1, color)

        time.sleep(SLEEP_TIME)

        for peer in self.peer_address:
            (code, tx_hash) = rpc_calls("sendtoaddress", peer, 1, color)

    def alliance_track(self):
        # pre_mint a lot for efficiency
        mint_tx_hash = self.mint(1, 0)

        # wait for a little time for the mint tx's confirmation
        print "%s : sleep %d sec" % (inspect.stack()[0][3], SLEEP_TIME)
        time.sleep(SLEEP_TIME)

        # randomly send license
        peer = random.choice(self.peer_address)
        color = random.randint(1, NUM_COLOR)
        (code, tx_hash) = rpc_calls("sendlicensetoaddress", peer, color)
        print "%s : send %s license to %s" % (inspect.stack()[0][3], \
                                              str(color), peer)

    def issuer_track(self):
        (code, out) = rpc_calls("getlicenseinfo")
        out = json.loads(out)
        all_license = out.keys()

        # activate all peers
        for i in all_license:
            if i not in self.license:
                self.license.append(i)
                self.activate(i)

        if len(all_license) != 0:
            print "%s : activate peers" % (inspect.stack()[0][3],)

        # mint money that we can mint
        for i in all_license:
            mint_tx_hash = self.mint(MINT_AMOUNT, i)

        if len(all_license) != 0:
            print "%s : mint money, color = %s, amount = %s" % \
                    (   inspect.stack()[0][3],
                        ' '.join(map(str, all_license)),
                        str(MINT_AMOUNT))

        # wait for a little time for the mint tx's confirmation
        if len(all_license) != 0:
            print "%s : sleep %d sec" % (inspect.stack()[0][3], SLEEP_TIME)
            time.sleep(SLEEP_TIME)

    def normal_track(self):
        (code, out) = rpc_calls("getbalance")
        out = json.loads(out)

        # send random color and random amount money randomly
        for color, money in out.items():
            if int(color) != 0:
                for peer in self.peer_address:
                    if random.randint(0, 100) == 0:
                        if int(money) // 5 >= 1:
                            money_out = random.randint(1, int(money) // 5)
                            tx_hash = self.rpc_calls("sendtoaddress", peer,
                                                     str(money_out),
                                                     str(color))[1]
                            print ("%s : send color = %s, amount = %s " +
                                  "to the %s") % (inspect.stack()[0][3],
                                                  str(color), str(money_out),
                                                  peer)

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
            error("Error : reset bitcoind failed\n")
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

        # use a stupid way to verify that if the tx is valid or not.
        # 64 is the len of txid
        if len(out) != 64:
            flag_complete = True
        else:
            flag_complete = False

        return flag_complete

    def is_alliance(self):
        (code, out) = rpc_calls("getmemberlist")
        out = json.loads(out)
        for i in out[u'member_list']:
            if i == str(self.wallet_address[0]):
                return True
        return False

    def wait_for_tx_confirmation(self, txid, flag_maturity=False,
                                 num_trial=10):
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

    def color_test(self, color):
        """ Return if the license transaction is valid

            return value:
                True,  if color is ok.
                False, if color is not ok.
                None,  if there is unexpected error.
        """

        if self.is_alliance() != True:
            error("Error: ", "You are not an alliance.")
            return None

        (code, txid) = rpc_calls("mint", 1, 0)
        print "Waiting for mint tx: {0} to be confirmed...".format(txid)

        flag_mint_confirmed = self.wait_for_tx_confirmation(txid, True)
        if not flag_mint_confirmed:
            return None

        (code, txid) = rpc_calls("sendlicensetoaddress",
                                 self.wallet_address[0], color)
        if code == RPC_ERROR_INVALID_COLOR:
            return False
        elif code != RPC_ERROR_INVALID_COLOR and code != RPC_SUCCESS:
            return None

#        print "Waiting for license tx: {0} to be confirmed...".format(txid)
        flag_license_confirmed = self.wait_for_tx_confirmation(txid)

        return None if flag_license_confirmed == False else True

    def usable_color_test(self):
        """ edge test 3-1 """

        flag_complete = True
        testing_color = [UINT32_MIN - 1, UINT32_MIN,
                         UINT32_MIN + 1, UINT32_MAX - 1,
                         UINT32_MAX, UINT32_MAX + 1]
        testing_answer = [False, None, True, True, True, False]

        for i in xrange(len(testing_color)):
            result = self.color_test(testing_color[i])
            if result != testing_answer[i]:
                error("Error :", "color %d failed, result=%r answer=%r"
                                    % (testing_color[i], result,
                                       testing_answer[i]))
                flag_complete = False

        return flag_complete

    def mint_amount(self):
        """ edge test 3-2

            [Caution]
            1. Mint amount should be integer
            2. Max amount is 10**10
            3. Using multiple colors to prevent from overflow of coins of
               one single color
        """
        MAX_AMOUNT = 10 ** 10

        flag_complete = True
        testing_color = [1, 2, 3, 4, 5, 6]
        testing_amount = [-1, 0, 1, MAX_AMOUNT - 1, MAX_AMOUNT, MAX_AMOUNT + 1]
        testing_answer = [False, False, True, True, True, False]

        # preparing for licenses

        for i in xrange(len(testing_amount)):
            if self.color_test(testing_color[i]) != True:
                error("Error :", "something wrong in creating license")
                return None
            code, out = rpc_calls("mint", testing_amount[i], testing_color[i])

            if code == RPC_SUCCESS:
                result = True
            elif code == RPC_ERROR_WALLET:
                result = False
            else:
                result = None

            if result != testing_answer[i]:
                error("Error :", "testing_amount %d failed" %
                                 testing_amount[i])
                flag_complete = False
        return flag_complete

    def __init__(self):
        self.reset_and_be_alliance()
        self.import_wallet_address()
        print self.mint_amount()
#        print self.usable_color_test()
#        print self.is_alliance()
#        print self.have_license(10)
#        self.import_peer_address()
#        print self.minting_without_license()
#        self._auto_run()

    def _auto_run(self):
        while True:
            if __debug__:
                self.alliance_track()
            else:
                self.issuer_track()
            self.normal_track()

if __name__ == "__main__":
    t = Test()
