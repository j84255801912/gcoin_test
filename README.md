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
Make sure that the machine you run on has installed gcoin, and the bitcoin.conf lays under ~/.bitcoin

### Auto test
#### Host
```
vim edge_test.py
```
Modify the list env.host to include your nodes domain name or ip.

For example,

env.hosts = ["core1.diqi.us", "core2.diqi.us", "127.0.0.1"]

#### Roles
There are only two roles defined now, alliance  nodes and ordinary nodes.
Modify the dictionary env.roledefs to define the role of your nodes. We can only add the alliance nodes to env.roledefs

For example, I want "127.0.0.1" to be "alliance", and the others are "others".

env.roledefs = {
    "alliance":     [127.0.0.1]
}

#### User and Passwords
Because fabric use ssh to manipulate nodes, we need the hosts' user & password.

For convinience, All hosts should use the same user and password.
Create a file named setting.py, and set user="your user name", password="the corresponding password"

For example,
in setting.py
```
user="kevin"
password="123"
```

It is ok that not using same user among hosts, and this section will be patched, soon.

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
For easy monitoring, redirect stdout to the file stdout, and stderr to file stderr.
```
(.env)$ python auto_test.py 1>stdout 2>stderr
```
