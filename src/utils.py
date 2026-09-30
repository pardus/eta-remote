import os
import socket
import struct
import fcntl

import uuid
import zlib

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
    # get uuid4
    uid = str(uuid.uuid4())
    # crc32 checksum
    uid = zlib.crc32(uid.encode("utf-8"))
    # hex string
    return str(hex(uid))[2:]
