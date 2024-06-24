import pysquared_rfm9x
import board
import busio
import digitalio
import traceback

import time
import os
import asyncio

import radio_diagnostics
from icpacket import Packet
from new_comms_protocol.ptp import AsyncPacketTransferProtocol as APTP
from new_comms_protocol.ftp import FileTransferProtocol as FTP

async def main():
	print("Irvington CubeSat's Test Satellite Board")
	
	# Constants
	# Chip's buffer size: 256 bytes
	# pycubed_rfm9x header size: 4 bytes
	# pycubed_rfm9x CRC16 checksum size: 2 bytes (DOES NOT take away from available bytes)
	# ptp header size: 6 bytes
	MAX_PAYLOAD_SIZE = 256 - 4 - 6 # 246
	# max length packets are bugged
	MAX_PAYLOAD_SIZE = MAX_PAYLOAD_SIZE - 1
	# msgpack adds 2 bytes overhead for bytes payloads
	CHUNK_SIZE = MAX_PAYLOAD_SIZE - 2 # 244
	TEST_IMAGE_PATH = "THBBlueEarthTest.jpeg"
	
	spi0 = busio.SPI(board.SPI0_SCK,board.SPI0_MOSI,board.SPI0_MISO)
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
	
	# Code from pysquared cubesat code - effect unknown
	# radio1_DIO0 = digitalio.DigitalInOut(board.RF1_IO0)
	# radio1_DIO0.switch_to_input()
	# radio1.DIO0 = radio1_DIO0
	# radio1.max_output = True
	
	ptp = APTP(radio1, packet_size=MAX_PAYLOAD_SIZE, timeout=10, log=False, enable_padding=False)  # padding is an optimization
	ftp = FTP(ptp, chunk_size=CHUNK_SIZE, packet_delay=0, log=False)
	
	radio_diagnostics.report_diagnostics(radio1)
	# st = time.monotonic()
	# radio1.send(b'1'*251)
	# print(time.monotonic()-st)
	# st = time.monotonic()
	# radio1.send(b'1'*252)
	# print(time.monotonic()-st)
	while True:
		try:
			print("Sending telemetry ping (handshake 1) and waiting for handshake 2")
			packet = Packet.make_handshake1()
			await ptp.send_packet(packet)
			packet = await ptp.receive_packet()
			if packet.categorize() != "handshake2":
				print(f"Packet of type {packet.categorize()} (not handshake2) received")
				continue
				
			print("Handshake 2 received, sending handshake 3")
			
			image_count = 420
			packet = Packet.make_handshake3(image_count)
			await ptp.send_packet(packet)
			
			print("Sending a picture")
			await ftp.send_file(TEST_IMAGE_PATH, file_id=69)
			
			print("20-sec cooldown period")
			time.sleep(20)
		
		except Exception as e:
			print("Error in Main Loop: "+ ''.join(traceback.format_exception(e)))

if __name__ == "__main__":
	asyncio.run(main())
