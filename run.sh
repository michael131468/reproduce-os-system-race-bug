#!/bin/sh

strace -f -s99999 -e trace=execve -e quiet="attach,exit,thread-execve" -Z python3 reproduce.py 2>&1 | grep -v "\-\-\- "

