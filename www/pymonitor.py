import os,sys,time,subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def log(s):
    print('[Monitor] %s ' % s)


class MyFileSystemEventHandler(FileSystemEventHandler):

    def __init__(self, fn):
        sum(MyFileSystemEventHandler, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            log('python source file changed:%s' % event.src_path)
            self.restart

command = ['echo', 'ok']
process = None


def killProcess():
    global process
    if process:
        log('kill process [%s]...' % process.pid)
        process.kill()
        process.wait()
        log('process ended with code %s' % process.returncode)
        process = None


def startProcess():
    global process, command
    log('start process %s...' % process.pid)
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restartProcess():
    killProcess()
    startProcess()


def startWatch(path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restartProcess), path, recursive=True)
    observer.start()
    log('watching directory %s...' % path)
    startProcess()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        print('Usage: ./pymonitor your-script.py')
        exit(0)
    if argv[0] != 'python3':
        argv.insert(0, 'python3')
    command = argv
    path = os.path.abspath('.')
    startWatch(path, None)

