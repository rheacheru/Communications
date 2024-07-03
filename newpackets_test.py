import pycubed_rfm9x
import board
import digitalio
import time
import wifi
from secrets import secrets
import socketpool
import adafruit_requests
import rtc
from adafruit_datetime import datetime
import traceback
import os
import asyncio
import radio_diagnostics
from new_comms_protocol.ptp import AsyncPacketTransferProtocol
from new_comms_protocol.ftp import FileTransferProtocol


async def main():
	print("Irvington CubeSat's Ground Station")
	
	CS = digitalio.DigitalInOut(board.D20)
	CS.switch_to_output(True)
	RST = digitalio.DigitalInOut(board.D21)
	RST.switch_to_output(True)

	RADIO_FREQ_MHZ = 437.4
	node = const(0xfb)
	destination = const(0xfa)
	MAX_PACKET_SIZE = 247

	radio = pycubed_rfm9x.RFM9x(board.SPI(), CS, RST, 437.4)
	radio.spreading_factor = 8
	radio.node = node
	radio.destination = destination
	radio.enable_crc = True
	
	PTP = AsyncPacketTransferProtocol(radio, packet_size=MAX_PACKET_SIZE, timeout=10, log=False)
	FTP = FileTransferProtocol(PTP, chunk_size=MAX_PACKET_SIZE, log=True)
	
	radio_diagnostics.report_diagnostics(radio)
	
	
	packet = PTP.Packet.make_handshake1()
	PTP.send_packet(packet)
	
	
	
if __name__ == "__main__":
	asyncio.run(main())

