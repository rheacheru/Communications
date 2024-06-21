import pysquared_rfm9x
import board
import busio
import digitalio
import traceback

import time
import os

from new_comms_protocol import ptp, ftp



'''
while True:
    try:
        radio1.send("Health of Cubesat: Healthy Haha")
        initial_packet = radio1.receive(timeout=10)
        print("received nothing")
        if initial_packet is None:
            continue
        print(initial_packet)
        if initial_packet != b'IRVCB':
            continue
        filepath = "THBBlueEarthTest.jpeg"
        size = os.stat(filepath)[6]
        
        with open(filepath, "rb") as image:
            radio1.send(bytearray([1]) + bytearray(size.to_bytes(4, "little")) + bytearray(image.read(244)))
            print("sent")
            packet_count = (size-1)//244+1
            for packet_index in range(2, packet_count+1):
                radio1.send(bytearray([1]) + bytearray(packet_index.to_bytes(4, "little")) + \
                    bytearray(image.read(244)))
                print("sent")
        radio1.send("Done")
        
        print("Sent image")
            
    except Exception as e:
        print("Error in Main Loop: "+ ''.join(traceback.format_exception(e)))
'''







MAX_PACKET_SIZE = 250
TEST_IMAGE_PATH = "THBBlueEarthTest.jpeg"

def main():
	print("Initializing main loop")
	
	spi0   = busio.SPI(board.SPI0_SCK,board.SPI0_MOSI,board.SPI0_MISO)
	_rf_cs1 = digitalio.DigitalInOut(board.SPI0_CS0)
	_rf_cs1.switch_to_output(value=True)
	_rf_rst1 = digitalio.DigitalInOut(board.RF1_RST)
	_rf_rst1.switch_to_output(value=True)
	radio1 = pysquared_rfm9x.RFM9x(spi0,_rf_cs1, _rf_rst1, 437.4, code_rate=8, baudrate=1320000)
	radio1.tx_power=23
	radio1.spreading_factor = 8
	radio1.node = 0xfa
	radio1.destination = 0xfb
	radio1.enable_crc=True
	radio1.ack_delay=0.2
	
	PTP = ptp.AsyncPacketTransferProtocol(radio1, packet_size=MAX_PACKET_SIZE, timeout=10, log=False)
	FTP = ftp.FileTransferProtocol(PTP, log=False)
	
	while True:
		try:
			print("Sending telemetry ping (handshake 1) and waiting for handshake 2")
			radio1.send(b"#IRVCB")
			packet = radio1.receive(timeout=10)
			if packet is None:
				continue
			packet = packet.decode("utf-8")
			if packet != "#IRVCBH2":
				continue
				
			print("Handshake 2 received, sending handshake 3")
			header = bytearray("#IRVCBH3", "utf-8")
			image_count = 420
			image_count_ba = bytearray(image_count.to_bytes(4, "little"))
			packet = header + image_count_ba
			radio1.send(packet)
			
			print("Sending a picture")
			FTP.send_file_sync(TEST_IMAGE_PATH)
			
			print("5-sec cooldown period")
			time.sleep(5)
		
		except Exception as e:
			print("Error in Main Loop: "+ ''.join(traceback.format_exception(e)))
		

if __name__ == "__main__":
	main()
