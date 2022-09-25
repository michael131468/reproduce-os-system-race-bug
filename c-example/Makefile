all: main

main: main.c
	gcc main.c -o main

run: main
	strace -f -s99999 -e trace=execve -e quiet="attach,exit,thread-execve" -Z ./main 2>&1 | grep -v "\-\-\-"
