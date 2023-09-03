#import pycubed_rfm9x
import time
import os


def send_image(filepath):
    size = os.path.getsize(filepath)
    #password = 13
    packet = size.to_bytes(4, byteorder = "big")
    pass


size = 234233211
p = 13

packet = size.to_bytes(6, byteorder="big")
password = p.to_bytes(1, byteorder="big")

packet = bytearray(packet)
packet[0] = 13
packet[1] = 1
for i in range(6):
    print(packet[i])