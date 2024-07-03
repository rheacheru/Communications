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
from adafruit_datetime import datetime
import traceback
from comms import file_receive
import os


CS = digitalio.DigitalInOut(board.D20)
CS.switch_to_output(True)
RST = digitalio.DigitalInOut(board.D21)
RST.switch_to_output(True)
print('hello')

RADIO_FREQ_MHZ = 437.4
node = const(0xfb)
destination = const(0xfa)

rfm9x = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
rfm9x.spreading_factor = 8
rfm9x.node = node
rfm9x.destination = destination

print("Waiting for messages...")
while True:
    try:
        #print('Waiting for messages....')
        packet = rfm9x.receive(timeout=10)
        if packet is None:
            continue
        
        print("Telemetry packet received.")
        filename = datetime.now().isoformat().replace(":","-")
        filepath =f'received_telemetry/{filename}.txt'
        rfm9x.send("IRVCB")

        packet = rfm9x.receive(timeout=10)
        if packet[0] != 1: # not an image packet
            print("Non-image packet received, rejected")
            continue
        print("First image packet received")
        
        size = int.from_bytes(packet[1:5], 'little')
        packet_count = (size-1)//244+1
        print(f"Image is of size {size} bytes, requiring {packet_count} packets")
        folder_path = f"received_images/{filename}"
        print("Wrote first image packet")
        request_packet_list = [0]*packet_count # 0 for not received correctly, 1 for received correctly
        request_packet_list[0] = 1
        
        for packet_index in range(2, packet_count+1):
            packet = rfm9x.receive(timeout=10)
            if packet is None or (len(packet)!=249 and packet_index < packet_count):
                request_packet_list[packet_number-1]=0
                print(packet)
                print('something went wrong')
            elif packet[0] == 1:
                packet_number = int.from_bytes(packet[1:5], 'little')
                packet_path = f"{folder_path}/packet_{packet_number}.raw"
                request_packet_list[packet_number-1] = 1
                print('received')
            else:
                request_packet_list[packet_number-1]=0
                print('something went wrong') 
           
            '''elif len(packet) != 249 and packet_index < packet_count:
                packet_path = f"corrupted/{datetime.now().isoformat()}.raw"
                print(f"Packet {packet_path} has length {len(packet)}, not 249")
                request_packet_list[packet_index -1] = 0

            elif packet[0] != 1:
                packet_path = f"corrupted/{datetime.now().isoformat()}.raw"
                print("image indicator bit missing")
                request_packet_list[packet_index - 1] = 0'''

        print('image created')
        print(f'request packet list: {request_packet_list}')
        packet = rfm9x.receive(timeout=10)
        print(packet)

    except Exception as e:
        print("Error in Main Loop: " + ''.join(traceback.format_exception(e)))