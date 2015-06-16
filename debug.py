from fabric.api import *
from fabric.context_managers import hide
from fabric.tasks import execute
from auto_test import parsing_hosts

@parallel
def get_debug_log_error():

    result = run('egrep \'(error|ERROR)\' ~/.bitcoin/gcoin/debug_* | awk \'{$1="";$2=""; print}\' | sort | uniq')
    return result

def see_all_debug_error():

    result = execute(get_debug_log_error)
    for key, value in result.items():
        print
        print key
        print "======================================"
        print value

if __name__ == "__main__":

    parsing_hosts()
    with hide('everything'):
        see_all_debug_error()
