#!/bin/bash
# usage     :   e.g.  ./reset.sh 201
killall bitcoind
sleep 3
#mv $HOME/.bitcoin/gcoin $HOME/.bitcoin/gcoin_`date +%Y%m%d%H%M%S`
rm -rf $HOME/.bitcoin/gcoin
bitcoind -gcoin -daemon
sleep 3
killall bitcoind
sleep 3
cp ./wallet.dat.$1 $HOME/.bitcoin/gcoin/wallet.dat
bitcoind -gcoin -daemon
