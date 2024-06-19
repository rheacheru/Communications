# Write your code here :-)
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
from ptp import AsyncPacketTransferProtocol
from ftp import FileTransferProtocol



def attempt_wifi():
    # TODO: Move wifi pass and id to config
    # try connecting to wifi
    print("Connecting to WiFi...")
    try:
        wifi.radio.connect(ssid=secrets["wifi"]["ssid"], password=secrets["wifi"]["password"])
        # wifi.radio.connect(ssid="Stanford") # open network
        print("Signal: {}".format(wifi.radio.ap_info.rssi))
        # Create a socket pool
        pool = socketpool.SocketPool(wifi.radio)
        # sync out RTC from the web
        synctime(pool)
    except Exception as e:
        print("Unable to connect to WiFi: {}".format(e))
        return None
    else:
        return pool    
        
def synctime(pool):
    try:
        requests = adafruit_requests.Session(pool)
        TIME_API = "http://worldtimeapi.org/api/ip"
        the_rtc = rtc.RTC()
        response = None
        while True:
            try:
                print("Fetching time")
                # print("Fetching json from", TIME_API)
                response = requests.get(TIME_API)
                break
            except (ValueError, RuntimeError) as e:
                print("Failed to get data, retrying\n", e)
                continue

        json1 = response.json()
        print(json1)
        current_time = json1['datetime']
        the_date, the_time = current_time.split('T')
        year, month, mday = [int(x) for x in the_date.split('-')]
        the_time = the_time.split('.')[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(':')]

        # We can also fill in these extra nice things
        year_day = json1['day_of_year']
        week_day = json1['day_of_week']
        is_dst = json1['dst']

        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst))
        the_rtc.datetime = now
    except Exception as e:
        print('[WARNING]', e)



def main():
    CS = digitalio.DigitalInOut(board.D20)
    CS.switch_to_output(True)
    RST = digitalio.DigitalInOut(board.D21)
    RST.switch_to_output(True)
    print('hello')

    RADIO_FREQ_MHZ = 437.4
    node = const(0xfb)
    destination = const(0xfa)
    MAX_PACKET_SIZE = 250

    radio = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
    radio.spreading_factor = 8
    radio.node = node
    radio.destination = destination
    radio.enable_crc(True)
    
    pool = attempt_wifi()
    
    PTP = AsyncPacketTransferProtocol(radio, packet_size=MAX_PACKET_SIZE, timeout=10, log=False)
    FTP = FileTransferProtocol(PTP, log=False)
    
    # async def send_packet(self, packet_type, payload, sequence_num=2**15 - 1):
    
    while True:
        try:
            print('Waiting for telemetry ping (handshake 1)')
            
            packet = radio.receive(timeout=10)
            if packet is None:
                continue
            packet = packet.decode("utf-8")
            if packet != "#IRVCB":
                continue
            print("Telemetry ping (handshake 1) received")
            
            radio.send(b"#IRVCBH2")
            print("Handshake 2 sent, waiting for handshake 3")
            
            # filepath =f'received_telemetry/{datetime.now().isoformat()}.txt'.replace(":", "-")
            # with open(filepath, 'w') as f:
            #     f.write(packet)
            #     print(f"Telemetry packet written to {filepath}")
            # radio.send("IRVCB")

            packet = radio.receive(timeout=10)
            if packet is None:
                continue
            identifier = packet[0:8].decode("utf-8")
            if identifier != "#IRVCBH3":
                continue
            print("Handshake 3 received")
            
            image_count = int.from_bytes(packet[8:12], "little")
            print(f"CubeSat has taken {image_count} images so far")
            
            # Start listening for image packets
            while True:
                packet_list, missing = FTP._receive_file()
                if packet_list is None:
                    break
                print(packet_list)
                print(missing)
            
            # Request images or return to standby
            
            
            '''
            
            if packet[0] != 1: # not an image packet
                print("Non-image packet received, rejected")
                continue
            print("First image packet received")
            
            size = int.from_bytes(packet[1:5], 'little')
            packet_count = (size-1)//244+1
            print(f"Image is of size {size} bytes, requiring {packet_count} packets")
            image_name = datetime.now().isoformat()
            folder_path = f"received_images/{image_name}"
            os.mkdir(folder_path)
            packet_path = f"{folder_path}/packet_1.raw"
            with open(packet_path,"wb") as f:
                f.write(packet[5:])
                print(f"Packet {packet_path} successfully saved")
            
            request_packet_list = [0]*packet_count # 0 for not received correctly, 1 for received correctly
            request_packet_list[0] = 1
            while True:
                packet = radio.receive(timeout=10)
                if packet is None:
                    print("Stopped receiving packets. Packet status list:")
                    print(request_packet_list)
                    break
                if packet[0] == 1 and len(packet) == 249:
                    packet_number = int.from_bytes(packet[1:5], 'little')
                    packet_path = f"{folder_path}/packet_{packet_number}.raw"
                    with open(packet_path, "wb") as f:
                        f.write(packet[5:])
                        print(f"Packet {packet_path} successfully saved")
                    request_packet_list[packet_number-1] = 1
                    if packet_number == packet_count:
                        print("Final packet was received. Packet status list:")
                        print(request_packet_list)
                        break
                elif len(packet) != 249:
                    packet_path = f"corrupted/{datetime.now().isoformat()}.raw"
                    with open(packet_path, "wb") as f:
                        f.write(packet)
                        print(f"Packet {packet_path} has length {len(packet)}, not 249")
                else: # packet[0] != 1
                    packet_path = f"corrupted/{datetime.now().isoformat()}.raw"
                    with open(packet_path, "wb") as f:
                        f.write(packet)
                        print(f"Packet {packet_path} starts with non-1")
                
            packet = radio.receive(timeout=10)
            print("Packet following image: ", packet)
            
            '''
        
        except Exception as e:
            print("Error in Main Loop: " + ''.join(traceback.format_exception(e)))

if __name__ == "__main__":
    main()
