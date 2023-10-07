# Write your code here :-)
import pycubed_rfm9x
import board
import digitalio
import busio
import time


CS = digitalio.DigitalInOut(board.D5)
CS.switch_to_output(True)
RST = digitalio.DigitalInOut(board.D6)
RST.switch_to_output(True)
print('hello')

RADIO_FREQ_MHZ = 437.4
node = const(0xfb)
destination = const(0xfa)

rfm9x = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
rfm9x.spreading_factor = 8
rfm9x.node = node
rfm9x.destination = destination
def main1():
    while True:
        packet = rfm9x.receive(timeout=10)
        #print('hi')
        if packet is not None:
            print(packet)
            print(rfm9x.last_rssi)

def main2():
    print('in main2')
    while True:
        current_time = time.time()
        path =f'/Volumes/CIRCUITPY/received_images/{current_time}.jpg'
        packet = rfm9x.receive()
        with open(path, "wb+") as stream:
            while True:
                data = rfm9x.receive()
                if data is None:
                    break
                stream.write(data)
                print('done')

main2()




