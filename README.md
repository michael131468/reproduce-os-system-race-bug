# reproduce-os-system-race-bug

This repository holds a reproduction case that demonstrates that Python's
os.system function is thread unsafe when used in parallel to adding variables
using os.environ.

# About

_Note that I believe this is actually a little bit deeper than just Python's
os.system and the reproduction case in this repository shows that execve has
a potential race condition with glibc's putenv when adding environment variables
from a separate thread._

This code is the result of investigating a random race condition bug in the
setup.py of uWSGI [1]. This bug manifested on my eight core laptop very
persistently and was very mysterious in failure. The bug led to some gcc
executions using os.system in Python threads failing randomly and if patched
to use subprocess.call then the bug was mitigated.

On my machine, it became more persistent the longer in length the CFLAGS
variable became and would disappear as the CFLAGS variable became smaller.

When I applied strace to debug it, I could see the `execve` syscall returning
with `-1 EFAULT`. This suggests a memory address became unreachable during the
execve call. I assumed I had found a potential race condition bug in cpython or
glibc where maybe the string holding the command line for os.system was being
freed before execve had finished copying [2] it. I assumed that this was
occuring more frequently as the command line string became longer as it would
take longer for execve to make a copy.

After digging through the code for cpython, glibc and the kernel, I could see
no point where a free before use could occur. Everything was chained together
and waited patiently for execve to finish before any memory was freed.

I tried to build a reproduction case with a similar setup to the code in uWSGI,
more specifically uwsgiconfig.py [3] where the bug manifested. I took the code
for spawning several worker threads and the loop that fed jobs to them to
execute and clean up before exit. I modified the worker threads to instead call
echo with long command line strings as I assumed it was related to these long
command line strings taking too much time to copy and triggering the race
condition. Running this for some time led to no success in reproducing the bug.

Meanwhile, I could almost persistently reproduce the bug when executing the
setup.py in uWSGI, so I knew there was something I'm missing in the reproduction
case.

I then thought it was maybe related to the workload itself and tried calling gcc
to compile bzip2 with large compiler flags leading to long command line strings.
I still could not reproduce the bug.

Next I introduced many large environment variables into the process and changed
the gcc executions to compile the C files from uWSGI to reduce the differences
with the uWSGI case. This was still unsuccessful.

I dissected further how the uWSGI python build works and learned that the build
is divided into three main steps:

  (1) compile the core code

  (2) compile the plugins

  (3) link the uwsgi binary together

I discovered if I toggled off the plugins compilation step then the bug would
disappear. In this plugins compilation step, it was using `exec` to execute the
python code from the plugins directly in the Python process before compiling
the related C code. This was what my reproduction case was missing.

Digging further, I found if I disabled the build of a certain plugin (named the
python plugin) then the bug would disappear. This plugin had some Python code
executed that would add an environment variable using os.environ [4]. I
commented out that line specifically and found the bug disappeared.

This showed that if the parent python process adds an environment variable
using `os.environ` while `execve` is being run by a thread then there is a
possibility that the execve call will fail. I believe this is because the
environment variables pointer being reallocated by `putenv` in glibc [5] leads
to a race with execve which will fail to access the original pointer during
its copying of the values.

I could then build the reproduction case in this repo with this informaton.
The reproduction case spawns 8 worker threads and feeds them with requests to
echo helloworld to /dev/null. In parallel to the worker threads, the main Python
process constantly adds environment variables using os.environ. On my laptop,
the workers consistently showed some random execution failures where os.system
returned an error. Applying strace (see run.sh) showed that the execve calls
would fail with -1 EFAULT which matched the bug seen in uWSGI.

I am still working out some of the details to understand this but the
reproduction case is clear. The python os.system command is not thread safe
when used in conjunction with adding environment variables using os.environ.
And this suggests putenv is thread unsafe when execve may be running.

One thing I am unclear of still is why the environment variables in the
threads are not copy-on-write as that should avoid the environment variable
pointer reference for the threads being affected by the parent thread. I
plan to continue to dig into this issue further to learn more about this.

Race condition issues with putenv have been long documented [5] so I suspect
this is nothing new to most C developers. To see this manifest in a higher
level language like Python shows that it's still important for developers to
learn and understand how the operating system works.

[1] https://github.com/unbit/uwsgi/issues/2447

[2] https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/exec.c#n514

[3] https://github.com/unbit/uwsgi/blob/2.0.20/uwsgiconfig.py

[4] https://github.com/unbit/uwsgi/blob/2.0.20/plugins/python/uwsgiplugin.py#L65

[5] https://github.com/lattera/glibc/blob/master/stdlib/setenv.c#L109

[6] http://www.club.cc.cmu.edu/~cmccabe/blog_the_setenv_fiasco.html

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
