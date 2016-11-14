#!/usr/bin/env python2
import os
import sys
import _imdo
import fcntl
import signal
import termios
import argparse

def remapfd(old, flags, new, daemonize):
    if new is None:
        if daemonize:
            os.close(old.fileno())
    else:
        old = old.fileno()
        new = os.open(new, flags)
        os.close(old)
        os.dup2(new, old)
        os.close(new)

def parent(args, mypipe, child_pid):
    sys.stdin.close()
    os.close(mypipe[1])
    with os.fdopen(mypipe[0], 'r') as rpipe:
        data = rpipe.read()
    for line in data.split('\n'):
        if line:
            sys.stdout.write(line + '\n')
            sys.stdout.flush()
            if line[0] == 'F':
                sys.exit(1)

class MockPipe(object):
    def close(self):
        pass

    def write(self, *args):
        sys.stderr.write(*args)

    def flush(self):
        sys.stderr.flush()

def child(args, mypipe):
    if mypipe:
        os.close(mypipe[0])
        wpipe = os.fdopen(mypipe[1], 'w')
    else:
        wpipe = MockPipe()

    for std, flags in (('stdin', os.O_RDONLY),
                       ('stdout', os.O_WRONLY | os.O_CREAT),
                       ('stderr', os.O_WRONLY | os.O_CREAT)):
        remapfd(getattr(sys, std), flags, getattr(args, std), args.daemonize)

    try:
        sid = os.setsid()
    except:
        sid = -1

    pid = os.getpid()
    pgid = os.getpgid(pid)
    sid = os.getsid(pid)
    if pid == pgid:
        wpipe.write('{}\n'.format(pgid))
    else:
        wpipe.write('Failed to setsid.\n')
        wpipe.close()
        sys.exit(1)

    if mypipe:
        try:
            fcntl_old = fcntl.fcntl(wpipe, fcntl.F_GETFD)
            fcntl.fcntl(wpipe, fcntl.F_SETFD, fcntl_old | fcntl.FD_CLOEXEC)
        except Exception as e:
            wpipe.write('Failed to set FD_CLOEXEC: {}.\n'.format(e));
            wpipe.close()
            raise

    if _imdo.disable_setsid():
        wpipe.write('Failed to disable setsid.\n')
        wpipe.close()
        sys.exit(1)

    if args.daemonize:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        try:
            tty = os.open('/dev/tty', os.O_RDWR)
            fcntl.ioctl(tty, termios.TIOCNOTTY)
        except:
            pass

    wpipe.flush()
    try:
        os.execvp(args.executable, [args.executable] + args.arguments)
    except Exception as e:
        wpipe.write('Failed to execvp: {}.\n'.format(e))
        wpipe.close()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Start a process in a new process group')

    std = parser.add_argument_group('Standard I/O Streams')
    std.add_argument('-i', '--stdin',
            help='File to open as stdin for the new process')
    std.add_argument('-o', '--stdout',
            help='File to open as stdout for the new process')
    std.add_argument('-e', '--stderr',
            help='File to open as stderr for the new process')

    parser.add_argument('-d', '--daemonize',
            action='store_true',
            help='Fork before running the new process')

    parser.add_argument('executable',
            help='The executable to launch')

    parser.add_argument('arguments',
            nargs=argparse.REMAINDER,
            help='Arguments to pass to the executable')

    args = parser.parse_args()

    if args.daemonize:
        mypipe = os.pipe()
        child_pid = os.fork()
    else:
        mypipe = None
        child_pid = 0

    if child_pid:
        parent(args, mypipe, child_pid)
    else:
        child(args, mypipe)

if __name__ == '__main__':
    main()
