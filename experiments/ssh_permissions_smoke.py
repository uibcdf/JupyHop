"""Default-config permission acceptance in an explicitly provisioned test account.

Requires m5_accounts prepare/provision/check. Never uses the operator's SSH
configuration. The exclusive synthetic config is removed by inode after testing.
"""

import argparse
import json
from importlib.resources import files
from pathlib import Path

from experiments.m5_accounts import _prepared, check
from jupyhop.ssh import SSHTransport

PROGRAM = r"""
import json,os,pwd,stat,subprocess,sys,types
payload=json.load(sys.stdin)
identity=pwd.getpwuid(os.getuid())
expected='jht_'+payload['token']+'_a'
if os.getuid()==0 or os.getuid()!=payload['uid'] or identity.pw_name!=expected or identity.pw_dir!='/home/'+expected:
    raise RuntimeError('Not the explicitly generated fixture account')
directory=os.open(identity.pw_dir+'/.ssh',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
descriptor=-1
original=None
try:
    info=os.fstat(directory)
    if info.st_uid!=os.getuid() or info.st_mode & 0o077:
        raise RuntimeError('Unexpected private fixture SSH directory')
    descriptor=os.open('config',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
    original=os.fstat(descriptor)
    os.write(descriptor,b'Host workstation\n    HostName workstation.example.org\n    User researcher\n')
    os.fsync(descriptor)
    for mode in (0o600,0o644,0o664):
        os.fchmod(descriptor,mode)
        result=subprocess.run(['/usr/bin/ssh','-G','workstation'],capture_output=True,timeout=5)
        if mode!=0o664:
            if result.returncode!=0:
                raise RuntimeError('Safe default configuration unexpectedly refused')
        elif result.returncode==0 or b'Bad owner or permissions' not in result.stderr:
            raise RuntimeError('Unsafe default configuration not refused')
    # Exercise the actual client classifier as this UID, without installing a
    # remote package or assuming the checkout is readable by the fixture UID.
    package=types.ModuleType('jupyhop')
    package.__path__=[]
    sys.modules['jupyhop']=package
    errors=types.ModuleType('jupyhop.errors')
    sys.modules['jupyhop.errors']=errors
    exec(compile(payload['errors'],'<fixture-errors>','exec'),errors.__dict__)
    module=types.ModuleType('fixture_ssh')
    sys.modules['fixture_ssh']=module
    namespace=module.__dict__
    exec(compile(payload['ssh'],'<fixture-ssh>','exec'),namespace)
    message=str(namespace['ssh_failure'](result.stderr))
    if 'group/other writes' not in message or 'chmod 600 ~/.ssh/config' not in message or identity.pw_dir in message:
        raise RuntimeError('Default-config remedy was not safely classified')
    print(json.dumps({'modes_checked':['0600','0644','0664'],'feedback':True}))
finally:
    if descriptor>=0:
        os.close(descriptor)
    try:
        current=os.stat('config',dir_fd=directory,follow_symlinks=False)
        if original is not None:
            if (current.st_dev,current.st_ino,current.st_uid)!=(original.st_dev,original.st_ino,os.getuid()):
                raise RuntimeError('Fixture config changed; refusing unrelated removal')
            os.unlink('config',dir_fd=directory)
    except FileNotFoundError:
        pass
    finally:
        os.close(directory)
"""


def run(root):
    root, token, _, _ = _prepared(root)
    check(root)
    ready = json.loads((root / "ready.json").read_text())
    payload = {
        "token": token,
        "uid": ready["users"][0]["uid"],
        "errors": files("jupyhop").joinpath("errors.py").read_text(),
        "ssh": files("jupyhop").joinpath("ssh.py").read_text(),
    }
    transport = SSHTransport("account-a", config=root / "ssh_config", timeout=30)
    result = transport.run(
        ["/usr/bin/python3", "-I", "-B", "-c", PROGRAM], stdin=json.dumps(payload).encode()
    )
    if result.returncode or json.loads(result.stdout) != {
        "modes_checked": ["0600", "0644", "0664"],
        "feedback": True,
    }:
        raise RuntimeError("Default SSH config acceptance failed; raw output suppressed")
    print(
        "PASS: native default config accepts 0600/0644, rejects 0664; ownership/write remedy is curated; exclusive fixture config removed"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    run(args.root)


if __name__ == "__main__":
    main()
