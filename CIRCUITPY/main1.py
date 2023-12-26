import pycubed_rfm9x
import board
import digitalio
import busio
import time
import wifi
from secrets import secrets
import socketpool
import adafruit_requests
import rtc
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import ssl

CS = digitalio.DigitalInOut(board.D12)
CS.switch_to_output(True)
RST = digitalio.DigitalInOut(board.D13)
RST.switch_to_output(True)
print('hello')

RADIO_FREQ_MHZ = 437.4
node = const(0xfb)
destination = const(0xfa)

rfm9x = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
rfm9x.spreading_factor = 8
rfm9x.node = node
rfm9x.destination = destination
def main():
    while True:
        packet = rfm9x.receive(timeout=10)
        #print('hi')
        if packet is not None:
            print(packet)
            print(rfm9x.last_rssi)

main()