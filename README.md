# reproduce-os-system-race-bug

This repository holds a reproduction case that demonstrates that Python's
os.system function is thread unsafe when used in parallel to adding variables
using os.environ.

# About

This is the result of investigating a random race condition bug in the setup.py
of uWSGI [1].

[1] https://github.com/unbit/uwsgi/issues/2447

# How to run

Simply execute run.sh (expects to be executed in same directory it exists in because it references ./reproduce.py).

Example output:

```
$ ./run.sh
[pid 1981587] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7c5d160 /* 82 vars */) = -1 EFAULT (Bad address)
[pid 1981586] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7c5d160 /* 82 vars */) = -1 EFAULT (Bad address)
[pid 1981593] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[pid 1981592] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[pid 1981594] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */ <unfinished ...>
)                                       = -1 EFAULT (Bad address)
[pid 1981591] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[pid 1981590] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[pid 1981589] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[pid 1981588] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x5632d7cb1b50 /* 6 vars */) = -1 EFAULT (Bad address)
[thread 5][os.system failure] ouch! return code = 32512
[thread 3][os.system failure] ouch! return code = 32512
[thread 5][os.system failure] ouch! return code = 32512
[thread 3][os.system failure] ouch! return code = 32512
[thread 0][os.system failure] ouch! return code = 32512
[thread 7][os.system failure] ouch! return code = 32512
[thread 2][os.system failure] ouch! return code = 32512
[thread 4][os.system failure] ouch! return code = 32512
[thread 6][os.system failure] ouch! return code = 32512
```
