# gcoin_test
This test is composed of edge_test and auto_test, which are for gcoin testing.

Edge-test using python scripts to call bitcoin-rpc via shell.
Auto-test using fabric api to deploy multiple testing nodes.

## Installation

### python, pip
```
$ sudo apt-get install python python-pip
```
### virtualenv
```
$ sudo pip install virtualenv
```
### clone the code to your place
```
$ git clone https://github.com/j84255801912/gcoin_test.git
```
### setup environment
```
$ cd gcoin_test
$ virtualenv .env
(.env)$ source .env/bin/activate
(.env)$ pip install fabric
```

## Configuration
### Edge test
Make sure that the machine you run on has installed gcoin, and the bitcoin.conf lays under ``~/.bitcoin``

### Auto test
#### Host and Roles
```
vim test.conf
```
Modify the test.conf to include the hostname or ip you want.

For example,
```
# fill in hosts acting as alliances.
[alliance]
core1.diqi.us
127.0.0.1
140.112.29.201

# fill in hosts acting as normal nodes.
[others]

# choose one from above to act as monitor.
[monitor]
140.112.29.201
```

#### User and Passwords
Fabric use ssh to manipulate nodes, thus we need the hosts' user & password.

For convinience, All hosts should use the same user and password.

For example,
in test.conf
```
[user]
kevin
[password]
123
```

It is ok that not using same user among hosts, and tutorial for will be patched soon.

#### Other configurations
in auto_test.py

```
MATURITY = 11 # num of blocks that the coinbase tx need to become spendable
NUM_ADDRESSES = 100 # num of address per host
PORT = 55888 # the port the hosts listen to
NUM_COLORS = 1000 # num of color you want to use
MINT_AMOUNT = 1000 # the mint amount per mint transaction
```

## Run
### Edge test
```
$ python edge_test.py
```
### Auto test
```
(.env)$ python auto_test.py
```
The stdout and stderr will be redirected to files named stdout and stderr.

## Trouble Shooting
If the auto_test doesnt work correctly, you should confirm that the following settings are  right set.

* firewall settings
* dependency requirement
* virtualenv
* If hosts machines port is occupied by the others users?
* Can the bitcoinds launch easily on hosts machines?
