import os
import socket
import struct
import fcntl
import json
import secrets

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "config.json")
if os.path.isfile("/etc/pardus/eta-remote.json"):
    CONFIG_PATH = "/etc/pardus/eta-remote.json"


def load_config(path=None):
    """Load and return the configuration from config.json."""
    config_file = path or CONFIG_PATH
    with open(config_file, "r") as f:
        return json.load(f)

def get_local_ip():
    ret = []
    for ifname in os.listdir("/sys/class/net"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15].encode("utf-8"))
            )[20:24])
            if ifname != "lo":
                ret.append((ip, ifname))
        except Exception as e:
            print(e)
    return ret


def get_uid():
    # crc32 of a uuid was only 32 bits, keep the room id hard to guess
    return secrets.token_hex(8)
