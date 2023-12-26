from pysquared import cubesat as c
import functions 
import time
import os

def send_image(filepath):
    size = int(os.stat(filepath)[6])
    #password = 13
    packet = size.to_bytes(6, byteorder = "big")
    packet = bytearray(packet)
    packet[0] = 13 #password
    packet[1] = 1 #indicator for images
    c.radio1.send(packet)
    with open(filepath, "rb") as stream:
        while True:
            data = stream.read(249)
            if not data:
                break
            c.radio1.send(data)
            print('sent')
            time.sleep(2)
send_image('kitty.png')


    




