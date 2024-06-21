"""
`ptp`
====================================================

Simple CircuitPython compatible packet transfer protocol
Adapted from Stanford PyGS: https://github.com/stanford-ssi/PyGS
Modified for pycubed_rfm9x

"""
import binascii
import io

import msgpack


class AsyncPacketTransferProtocol:
    """A simple transfer protocol for commands and data"""

    def __init__(self, protocol, packet_size=252, timeout=1, log=False):
        self.protocol = protocol
        self.packet_size = packet_size
        self.timeout = timeout # Modified
        self.log = log
        self.tmp_stream = io.BytesIO()
        self.out_stream = io.BytesIO()
        self.data_packet = 0
        self.cmd_packet = 1
        self.header_len = 3

    def write_packet_into_out_stream(self, packet_type, payload, sequence_num):
        self.out_stream.seek(0)
        self.tmp_stream.seek(0)
        if packet_type != self.cmd_packet and packet_type != self.data_packet:
            print("packet type error")
            return -1
        elif sequence_num > 2**15 - 1:
            print("sequence num error")
            return -1
        else:
            msgpack.pack(payload, self.tmp_stream)
            payload_len = self.tmp_stream.tell()
            self.tmp_stream.seek(0)
            if payload_len > self.packet_size: # Modified
                print(f"packet too long ({payload_len} bytes, limit is {self.packet_size})")
                return -1
            header = (packet_type << 23) | (payload_len << 15) | sequence_num
            if self.log:
                print(f"header: {header}")
            if self.log:
                print(f"packet type: {packet_type}")
            if self.log:
                print(f"payload len: {payload_len}")
            if self.log:
                print(f"sequence num: {sequence_num}")
            if self.log:
                print(f"pycubed sending packet: {self.tmp_stream.getvalue()}")
            header_arr = bytearray(3)
            header_arr[0] = (header >> 2 * 8) & 0xFF
            header_arr[1] = header >> 8 & 0xFF
            header_arr[2] = header & 0xFF
            self.out_stream.write(header_arr)
            self.out_stream.write(self.tmp_stream.read(payload_len))
            self.out_stream.seek(0)
            self.tmp_stream = io.BytesIO()  # TODO fix this.
            self.tmp_stream.seek(0)
            return payload_len

    def send_cmd_packet_sync(self, command):
        payload_len = self.write_packet_into_out_stream(
            self.cmd_packet, command, 2**15-1
        )
        if payload_len == -1:
            return False
        self.out_stream.seek(0)
        if self.log:
            print(f"wrote data: {self.out_stream.read(252)}")
        self.out_stream.seek(0)
        success = self.protocol.send_with_ack(self.out_stream.read(252))
        if self.log:
            print("waiting for ack...")
        if not success:
            if self.log:
                print("did not receive ack")
            return False
        if self.log:
            print("received ack")

    def send_data_packet_sync(self, payload, sequence_num=2**15 - 1):
        payload_len = self.write_packet_into_out_stream(
            self.data_packet, payload, sequence_num
        )
        if payload_len == -1:
            return False
        self.out_stream.seek(0)
        if self.log:
            print(f"wrote data: {self.out_stream.read(252)}")
        self.out_stream.seek(0)
        self.protocol.send(self.out_stream.read(252))
        self.out_stream.seek(0)
        return True

    async def send_packet(self, packet_type, payload, sequence_num=2**15 - 1):
        print("Called with payload:")
        print(payload)
        payload_len = self.write_packet_into_out_stream(
            packet_type, payload, sequence_num
        )
        if payload_len == -1:
            return False
        if packet_type == self.cmd_packet:
            self.out_stream.seek(0)
            if self.log:
                print(f"wrote data: {self.out_stream.read(252)}")
            self.out_stream.seek(0)
            success = await self.protocol.send_with_ack(self.out_stream.read(252))
            if self.log:
                print("waiting for ack...")
            if not success:
                if self.log:
                    print("did not receive ack")
                return False
            if self.log:
                print("received ack")
        else:
            self.out_stream.seek(0)
            if self.log:
                print(f"wrote data: {self.out_stream.read(252)}")
            self.out_stream.seek(0)
            self.protocol.send(self.out_stream.read(252))
        self.out_stream.seek(0)
        return True
    
    
    async def receive_packet(self, with_ack=False):
        packet = self.protocol.receive(timeout=self.timeout, with_ack=with_ack) # Modified
        if packet is None:
            return False, False
        
        header = int.from_bytes(packet[0:3], "big")
        packet_type = header >> 23
        payload_len = (header >> 15) & (2**8 - 1)
        sequence_num = header & (2**15 - 1)
        if self.log:
            print(f"header: {header}")
            print(f"packet type: {packet_type}")
            print(f"payload len: {payload_len}")
            print(f"sequence num: {sequence_num}")
        self.tmp_stream = io.BytesIO()
        if self.log:
            print(f"tmp stream before rw: {self.tmp_stream.getvalue()}")
        self.tmp_stream.seek(0)
        self.tmp_stream.write(packet[3:]) # Modified
        if self.log:
            print(f"tmp stream before write: {self.tmp_stream.getvalue()}")
            self.tmp_stream.seek(0)
            print(f"payload_packed: {self.tmp_stream.read(payload_len)}")
        self.tmp_stream.seek(0)
        try:
            payload = msgpack.unpack(self.tmp_stream)  # TODO make this the same?
        except TypeError:
            print(f"Unexpected structure: {self.tmp_stream.getvalue()}")
            return False, False
        except ValueError:
            print(f"Failed to decode: {self.tmp_stream.getvalue()}")
            return False, False
        except Exception as e:
            print(f"Unknown exception: {self.tmp_stream.getvalue()} {e}")
            return False, False
        else:
            if packet_type == self.cmd_packet:
                print("pycubed sending ACK")
                self.protocol.send(b"ACK")
            self.tmp_stream = io.BytesIO()
            self.tmp_stream.seek(0)
            if self.log:
                print(f"payload: {payload}")
            return payload, sequence_num
        finally:
            self.tmp_stream = io.BytesIO()
            self.tmp_stream.seek(0)
    
    def crc32(self, packet_type, payload):
        packet_bytes = b""
        if isinstance(payload, int):
            packet_bytes = str(payload).encode("ascii")
        elif isinstance(payload, list):
            packet_bytes = str(payload).encode("ascii")
        elif isinstance(payload, bytes):
            packet_bytes = payload
        elif isinstance(payload, str):
            packet_bytes = payload.encode("ascii")
        return binascii.crc32(packet_bytes, 0).to_bytes(4, "big")

