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

class Test(object):
    mint_amount = 1000
    color_number = 100
    sleep_time = 15
    license = []

    def error(self, *args):
        sys.stderr.write(' '.join(map(str, args)) + '\n')
    def rpc_calls(self, *args):
        args = [i for i in args]
        try:
            p = Popen(["bitcoin-cli", "-gcoin"] + args, stdout=PIPE, stdin=PIPE, stderr=PIPE)
            out = p.communicate(input = "")[0].replace("\n", "")
        except Exception, e:
            self.error("Error : ", e)
        return out

    def import_wallet_address(self):
        self.wallet_address = json.loads(self.rpc_calls("listwalletaddress"))
        print "%s : done" % (inspect.stack()[0][3],)
    def import_peer_address(self):
        self.peer_address = peer_addresses
        print "%s : done" % (inspect.stack()[0][3],)

    def mint(self, amount, color):
        return self.rpc_calls("mint", str(amount), str(color))
    def activate(self, color):
        for i in xrange(len(self.peer_address)):
            self.mint(1, color)

        time.sleep(self.sleep_time)

        for peer in self.peer_address:
            tx_hash = self.rpc_calls("sendtoaddress", peer, str(1), str(color))
    def alliance_track(self):
        # pre_mint a lot for efficiency
        mint_tx_hash = self.mint(1, 0)

        # wait for a little time for the mint tx's confirmation
        print "%s : sleep %d sec" % (inspect.stack()[0][3], self.sleep_time)
        time.sleep(self.sleep_time)

        # randomly send license
        peer = random.choice(self.peer_address)
        color = random.randint(1, self.color_number)
        tx_hash = self.rpc_calls("sendlicensetoaddress", peer, str(color))
        print "%s : send %s license to %s" % (inspect.stack()[0][3], str(color), peer)
    def issuer_track(self):
        out = json.loads(self.rpc_calls("getlicenseinfo"))
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
            mint_tx_hash = self.mint(self.mint_amount, i)
        if len(all_license) != 0:
            print "%s : mint money, color = %s, amount = %s" % (inspect.stack()[0][3], ' '.join(map(str, all_license)), str(self.mint_amount))

        # wait for a little time for the mint tx's confirmation
        if len(all_license) != 0:
            print "%s : sleep %d sec" % (inspect.stack()[0][3], self.sleep_time)
            time.sleep(self.sleep_time)

    def normal_track(self):
        # get all available balance
        out = json.loads(self.rpc_calls("getbalance"))

        # send random color and random amount money randomly
        for color, money in out.items():
            if int(color) != 0:
                for peer in self.peer_address:
                    if random.randint(0, 100) == 0:
                        # 5 is the magic number
			if int(money) // 5 >= 1:
                        	money_out = random.randint(1, int(money) // 5)
                        	tx_hash = self.rpc_calls("sendtoaddress", peer, str(money_out), str(color))
                        	print "%s : send color = %s, amount = %s to the %s" % (inspect.stack()[0][3], str(color), str(money_out), peer)
    def __init__(self):
        self.import_wallet_address()
        self.import_peer_address()
        self._poll()
    def _poll(self):
        while True:
            if __debug__:
                self.alliance_track()
            else:
                self.issuer_track()
            self.normal_track()
if __name__ == "__main__":
    t = Test()
