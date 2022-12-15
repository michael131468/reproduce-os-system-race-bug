# reproduce-os-system-race-bug

This is a for education purposes reproduction case that demonstrates that
Python's os.system function is thread unsafe when used in parallel with adding
environment variables using os.environ.

## About

The following is the result of investigating a random race condition bug in the
setup.py of [uWSGI][1]. The bug was manifesting as random failed executions of
gcc using os.system in Python threads causing the setup to exit early as failed.
If the [code was patched to use subprocess.call instead of os.system][2], then
the bug appeared to be mitigated and the errors disappeared.

Since this uWSGI bug manifested on my eight core laptop very persistently and
was very mysterious in failure, it caught my eye and ended up educating me on
some fundamentals with system calls and glibc.

## The Debugging Story

To story starts with me trying to build the s2i-python-container images to fix
an unrelated bug but continuously hitting random failures that blocked me. I
noticed this kept occurring when the image build was trying to install the uWSGI
python module. 

Debugging this by building the s2i-python-container images was not trivial as it
was a significant overhead for debugging so I decided to first check if the
issue was reproducible by running the uWSGI setup.py installer directly. At
first I couldn’t get a clean reproduction but after copying the CFLAGS from the
s2i-python-container logs into the environment (luckily uWSGI automatically
inherited it from the env) it began to reproduce the failure.

The key thing about the CFLAGS seemed to be its length. It was a quite long
string (at over ~4000 characters). On my machine, the failures when installing
uWSGI would became more persistent the longer in length the CFLAGS variable
became and would disappear as the CFLAGS variable became smaller.

When I applied strace to debug it, I could see the `execve` syscall returning
with `-1 EFAULT`. This suggests a memory address became unreachable during the
execve call. I assumed I had found a potential race condition bug in cpython or
glibc where maybe the string holding the command line for os.system was being
freed before [execve had finished copying it][3]. My first thought was that this
was occuring more frequently as the command line string became longer as it
would take longer for execve to make a copy.

After digging through the code for cpython, glibc and the kernel, I could see
no point where a free before use could occur. Everything was chained together
and waiting patiently for execve to finish before any memory was freed.

I tried to build a reproduction case with a similar setup to the code in uWSGI,
more specifically [uwsgiconfig.py][4] where the bug manifested. I took the code
for spawning several worker threads and the loop that fed jobs to them to
execute and clean up before exit. I modified the worker threads to instead call
echo with long command line strings as I assumed it was related to these long
command line strings taking too much time to copy and triggering the race
condition. Running this for some time led to no success in reproducing the bug.

Meanwhile, I could still persistently reproduce the bug when executing the
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
python plugin) then the bug would disappear. This plugin had some [Python code
executed that would add an environment variable using os.environ][5]. I
commented out that line specifically and found the bug disappeared.

## The Debugging Outcome

This debugging showed that if the parent python process adds an environment
variable using `os.environ` while `execve` is being run by a thread then there
is a chance that the execve call will fail. This is because the environment
variables array pointer [being reallocated by `putenv` in glibc][6] leads to a
race with the execve syscall which can then fail to access the original pointer
during its copying of the values.

Armed with this information, I could then build the reproduction case found in
this repo. The reproduction case spawns 8 worker threads and feeds them with
requests to echo helloworld to /dev/null. In parallel to the worker threads, the
main Python process constantly adds environment variables using os.environ. On
my laptop, the workers consistently showed some random execution failures where
os.system returned an error. Applying strace (see run.sh) showed that the execve
calls would fail with `-1 EFAULT` which matched the bug seen in uWSGI.

Race condition issues with putenv have been [long documented][7] so I suspect
this is nothing new to most systems programmers. Now that I knew what I was searching
for, I could find a [bug][8] had been filed to the Python project to document
that os.environ is not thread-safe for this exact issue.

To see this issue manifest in a higher level language like Python shows that
it's still important for developers who are working in abstractions far above
the operating system to learn and understand how the operating system works.

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

# C Example

I've added a smaller example in C that shows this behaviour using system.3 and putenv.3.

Compile with `make all` and run with the `make run`.

```
$ make all
gcc main.c -o main

$ make run
strace -f -s99999 -e trace=execve -e quiet="attach,exit,thread-execve" -Z ./main 2>&1 | grep -v "\-\-\-"
[pid 3099883] execve("/bin/sh", ["sh", "-c", "echo helloworld > /dev/null"], 0x1212120 /* 16 vars */) = -1 EFAULT (Bad address)
cmd failed! error=32512
302 successful runs before failure
```

[1]: https://github.com/unbit/uwsgi/issues/2447
[2]: https://github.com/unbit/uwsgi/pull/2448
[3]: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/fs/exec.c#n514
[4]: https://github.com/unbit/uwsgi/blob/2.0.20/uwsgiconfig.py
[5]: https://github.com/unbit/uwsgi/blob/2.0.20/plugins/python/uwsgiplugin.py#L65
[6]: https://github.com/lattera/glibc/blob/master/stdlib/setenv.c#L109
[7]: http://www.club.cc.cmu.edu/~cmccabe/blog_the_setenv_fiasco.html
[8]: https://bugs.python.org/issue39375
