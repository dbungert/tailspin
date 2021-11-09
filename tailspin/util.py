
import os


def generate_logfile_name(command, basedir, runid):
    '''
    Alter a command path to turn it into a descriptive log file name that looks
    similar to that command path, but is stripped of special characters.
    '''
    # this helps resolve weirdness like ./a/./b and turns it into ./a/b
    command = os.path.normpath(command)
    # no leading dots
    while command[0] == '.':
        command = command[1:]
    # no leading slash
    if command[0] == '/':
        command = command[1:]
    # remaining slashes become dashes
    descriptor = command.replace('/', '-')
    padded_runid = str(runid).zfill(4)
    return f'{basedir}/{descriptor}-{padded_runid}.log'

def create_logdir():
    os.makedirs('logs', exist_ok=True)
    for dirid in range(1, 999):
        padded_dirid = str(dirid).zfill(3)
        target = os.path.join('logs', padded_dirid)
        if not os.path.exists(target):
            os.makedirs(target)
            return target
    return None
