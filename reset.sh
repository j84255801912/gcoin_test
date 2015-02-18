#!/bin/bash
# usage     :   e.g.  ./reset.sh 201
killall bitcoind
mv $HOME/.bitcoin/gcoin $HOME/.bitcoin/gcoin_`date +%Y%m%d%H%M`
bitcoind -gcoin -daemon
sleep 2
killall bitcoind
cp ./wallet.dat.$1 $HOME/.bitcoin/gcoin/wallet.dat
bitcoind -gcoin -daemon
