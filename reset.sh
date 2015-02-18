#!/bin/bash
# usage     :   e.g.  ./reset.sh 201
bitcoin-cli -gcoin stop
mv $HOME/.bitcoin/gcoin $HOME/.bitcoin/gcoin_`date +%s`
bitcoind -gcoin -daemon
bitcoin-cli -gcoin stop
cp ./wallet.dat.$1 $HOME/.bitcoin/gcoin/wallet.dat
bitcoind -gcoin -daemon
