#!/usr/bin/env python3

import os

from queue import Queue
from threading import Thread,Lock

global thread_lock, work_queue, thread_workers

NUM_OF_THREADS = 8
work_queue = Queue(maxsize=NUM_OF_THREADS)
thread_lock = Lock()
thread_workers = []

def thread_worker(num):
    while True:
        work_item = work_queue.get()
        if not work_item:
            return
        ret = os.system("echo helloworld > /dev/null")
        if ret != 0:
            thread_lock.acquire()
            print(f"[thread {num}][os.system failure] ouch! return code = {ret}")
            thread_lock.release()

# Stick a long variable into os.environ to make realloc of os.environ
# when adding a new variable slower
os.environ['A'] = "a" * 16000

# Spawn compiler threads and have them wait for messages to echo
for i in range(0, NUM_OF_THREADS):
    t = Thread(target=thread_worker, args=(i,))
    t.daemon = True
    t.start()
    thread_workers.append(t)

# Send jobs to all worker threads to start
for i in range(0, 10000):
    work_queue.put(1)

# Begin trying to race os.environ adding variables and execve
# Runs in parallel to worker threads
for i in range(0, 1000):
    os.environ['%s' % i] = "%s" % i

# Request all compiler threads to stop
for t in thread_workers:
    work_queue.put(None)
for t in thread_workers:
    t.join()
