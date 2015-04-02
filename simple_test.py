#!/usr/bin/python2.7
#
# author    :   kevin
# date      :   20150217
# purpose   :   very simple test for diqi

import inspect
import json
import random
import sys
import time

from subprocess import Popen, PIPE, STDOUT
from peer_addresses import peer_addresses

def error(*args):
    sys.stderr.write(' '.join(map(str, args)) + '\n')

'''
def rpc_decorator(func):
    def decorated(*args, **kwargs):
        out = func(*args, **kwargs)
        try:
            return json.loads(out)
        except ValueError:
            return None
    return decorated

def ensure_bitcoind_alive(func):
    def decorated(*args, **kwargs):
        
'''

#@rpc_decorator
def rpc_calls(*args, **kwargs):
    args = [str(i) for i in args]
    try:
        p = Popen(["bitcoin-cli", "-gcoin"] + args, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        out = p.communicate(input = "")[0].replace("\n", "")
    except Exception, e:
        error("Error : ", e)
        return None
    return out

class Test(object):
    """Testing"""

    UINT32_MAX = 2 ** 32 - 1
    UINT32_MIN = 0
    MINT_AMOUNT = 1000
    COLOR_NUMBER= 100
    SLEEP_TIME = 15
    MATURITY = 11
    license = []

    def import_wallet_address(self):
        self.wallet_address = json.loads(rpc_calls("listwalletaddress"))
        print "%s : done" % (inspect.stack()[0][3],)

    def import_peer_address(self):
        self.peer_address = peer_addresses
        print "%s : done" % (inspect.stack()[0][3],)

    def mint(self, amount, color):
        return rpc_calls("mint", amount, color)

    def activate(self, color):
        for i in xrange(len(self.peer_address)):
            self.mint(1, color)

        time.sleep(self.SLEEP_TIME)

        for peer in self.peer_address:
            tx_hash = rpc_calls("sendtoaddress", peer, 1, color)

    def alliance_track(self):
        # pre_mint a lot for efficiency
        mint_tx_hash = self.mint(1, 0)

        # wait for a little time for the mint tx's confirmation
        print "%s : sleep %d sec" % (inspect.stack()[0][3], self.SLEEP_TIME)
        time.sleep(self.SLEEP_TIME)

        # randomly send license
        peer = random.choice(self.peer_address)
        color = random.randint(1, self.COLOR_NUMBER)
        tx_hash = rpc_calls("sendlicensetoaddress", peer, color)
        print "%s : send %s license to %s" % (inspect.stack()[0][3], \
                                              str(color), peer)

    def issuer_track(self):
        out = json.loads(rpc_calls("getlicenseinfo"))
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
            mint_tx_hash = self.mint(self.MINT_AMOUNT, i)

        if len(all_license) != 0:
            print "%s : mint money, color = %s, amount = %s" % \
                    (   inspect.stack()[0][3],
                        ' '.join(map(str, all_license)),
                        str(self.MINT_AMOUNT))

        # wait for a little time for the mint tx's confirmation
        if len(all_license) != 0:
            print "%s : sleep %d sec" % (inspect.stack()[0][3], self.SLEEP_TIME)
            time.sleep(self.SLEEP_TIME)

    def normal_track(self):
        out = json.loads(rpc_calls("getbalance"))

        # send random color and random amount money randomly
        for color, money in out.items():
            if int(color) != 0:
                for peer in self.peer_address:
                    if random.randint(0, 100) == 0:
                        # 5 is the magic number
			if int(money) // 5 >= 1:
                        	money_out = random.randint(1, int(money) // 5)
                        	tx_hash = self.rpc_calls("sendtoaddress", peer,
                                                str(money_out), str(color))
                        	print "%s : send color = %s, amount = %s to the %s" \
                                        % (inspect.stack()[0][3], str(color),
                                            str(money_out), peer)

    def have_license(self, color):
        # fetch licenses
        out = json.loads(rpc_calls("getlicenseinfo"))
        all_license = out.keys()

        licenses = map(int, all_license)
        return True if color in licenses else False

    def minting_without_license(self):
        """ edge test 1-2 """

        flag_complete = False

        # fetch licenses
        out = json.loads(rpc_calls("getlicenseinfo"))
        all_license = out.keys()

        # find a color whose license is not belonged to us
        licenses = map(int, all_license)
        color = 1
        while True:
            if color not in licenses:
                break
            color += 1

        out = rpc_calls("mint", self.MINT_AMOUNT, color)

        # use a stupid way to verify that if the tx is valid or not.
        # 64 is the len of txid
        if len(out) != 64:
            flag_complete = True
        else:
            flag_complete = False

        return flag_complete

    def is_alliance(self):
        out = json.loads(rpc_calls("getmemberlist"))
        for i in out[u'member_list']:
            if i == str(self.wallet_address[0]):
                return True
        return False

    def wait_for_tx_confirmation(self, txid, flag_maturity=False, num_trial=10):
        """ Keep pooling bitcoind to get tx's confirmations. """

        count = 0
        while True:
            out_string = rpc_calls("getrawtransaction", txid, 1)
            try:
                out = json.loads(out_string)
            except:
                error("Error: ", out_string)
                return False

            keys = map(str, out.keys())
            if 'confirmations' in keys:
                if not flag_maturity:
                    return True
                else:
                    if int(out['confirmations']) >= self.MATURITY:
                        return True
            if count >= num_trial:
                return False
            count += 1
            time.sleep(1)

    def color_test(self, color):
        """ Return if the license transaction is valid """

        if self.is_alliance() != True:
            error("Error: ", "You are not an alliance.")
            return False

        txid = rpc_calls("mint", 1, 0)
        print "Waiting for mint tx: {0} to be confirmed...".format(txid)
        flag_mint_confirmed = self.wait_for_tx_confirmation(txid, True)

        if not flag_mint_confirmed:
            return False
        else:
            txid = rpc_calls("sendlicensetoaddress", self.wallet_address[0],
                            color)
            print txid
            print "Waiting for license tx: {0} to be confirmed...".format(txid)
            return self.wait_for_tx_confirmation(txid)

    def usable_color_test(self):
        # should be invalid transactions
        if self.color_test(self.UINT32_MAX + 1):
            error("Error :", "failed in testing %d" % (self.UINT32_MAX + 1))
            flag_complete = False

        if self.color_test(self.UINT32_MIN - 1):
            error("Error :", "failed in testing %d" % (self.UINT32_MIN - 1))
            flag_complete = False

        # should be valid transactions
        if self.color_test(self.UINT32_MAX):
            error("Error :", "failed in testing %d" % (self.UINT32_MAX))
            flag_complete = False

        if self.color_test(self.UINT32_MAX - 1):
            error("Error :", "failed in testing %d" % (self.UINT32_MAX - 1))
            flag_complete = False

        if self.color_test(self.UINT32_MIN):
            error("Error :", "failed in testing %d" % (self.UINT32_MIN))
            flag_complete = False

        if self.color_test(self.UINT32_MIN + 1):
            error("Error :", "failed in testing %d" % (self.UINT32_MIN + 1))
            flag_complete = False

        return True

    def __init__(self):
        self.import_wallet_address()
        print self.usable_color_test()
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
    pass
