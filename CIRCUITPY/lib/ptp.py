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
        self.max_packet_total_size = 252 # pycubed_rfm9x
        
        self.timeout = timeout # Modified
        self.log = log
        self.tmp_stream = io.BytesIO()
        self.out_stream = io.BytesIO()
        self.MAX_SIZE = self.max_packet_total_size
    
    # Constants
    data_packet = 0
    cmd_packet = 1
    header_len = 6 
    
    MAX_SEQUENCE_NUM = 2**19-1
    MAX_PAYLOAD_ID = 2**20-1
    
    class Packet:
        '''
        Our custom packet class.
        Details of each packet categorization are below.
        
        Category     Type   Payload
        handshake1   cmd    ["#IRVCB", -1]
        handshake2   cmd    ["#IRVCBH2", -1]
        handshake3   cmd    ["#IRVCBH3", image_count]
        file_len     cmd    packet_count 
        file_data    data   chunk_data
        '''
        def __init__(self, packet_type, sequence_num, payload_id, payload):
            self.packet_type = packet_type
            self.sequence_num = sequence_num
            self.payload_id = payload_id
            self.payload = payload
            self.data_packet = AsyncPacketTransferProtocol.data_packet
            self.cmd_packet = AsyncPacketTransferProtocol.cmd_packet
            self.MAX_SEQUENCE_NUM = AsyncPacketTransferProtocol.MAX_SEQUENCE_NUM
            self.MAX_PAYLOAD_ID = AsyncPacketTransferProtocol.MAX_PAYLOAD_ID

        def categorize(self):
            try:
                if self.packet_type is None:
                    return "none"
                if self.packet_type == self.cmd_packet:
                    if isinstance(self.payload, list) and len(self.payload) > 0:
                        if self.payload[0] == "#IRVCB":
                            return "handshake1"
                        elif self.payload[0] == "#IRVCBH2":
                            return "handshake2"
                        elif self.payload[0] == "#IRVCBH3":
                            return "handshake3"
                    return "file_len"
                else:
                    return "file_data"
            except Exception as e:
                print("Error categorizing packet:", e)

        @staticmethod
        def make_handshake1():
            return AsyncPacketTransferProtocol.Packet(
                AsyncPacketTransferProtocol.cmd_packet,
                AsyncPacketTransferProtocol.MAX_SEQUENCE_NUM,
                AsyncPacketTransferProtocol.MAX_PAYLOAD_ID,
                ["#IRVCB", -1]
            )
        
        @staticmethod
        def make_handshake2():
            return AsyncPacketTransferProtocol.Packet(
                AsyncPacketTransferProtocol.cmd_packet,
                AsyncPacketTransferProtocol.MAX_SEQUENCE_NUM,
                AsyncPacketTransferProtocol.MAX_PAYLOAD_ID,
                ["#IRVCBH2", -1]
            )
        
        @staticmethod
        def make_handshake3(image_count):
            return AsyncPacketTransferProtocol.Packet(
                AsyncPacketTransferProtocol.cmd_packet,
                AsyncPacketTransferProtocol.MAX_SEQUENCE_NUM,
                AsyncPacketTransferProtocol.MAX_PAYLOAD_ID,
                ["#IRVCBH3", image_count]
            )
        
        @staticmethod
        def make_file_len(payload_id, packet_count):
            return AsyncPacketTransferProtocol.Packet(
                AsyncPacketTransferProtocol.cmd_packet,
                AsyncPacketTransferProtocol.MAX_SEQUENCE_NUM,
                payload_id,
                -packet_count
            )
        
        @staticmethod
        def make_file_data(sequence_num, payload_id, chunk):
            return AsyncPacketTransferProtocol.Packet(
                AsyncPacketTransferProtocol.data_packet,
                sequence_num,
                payload_id,
                chunk
            )
        
    def logger(self, *messages):
        if self.log:
            for m in messages:
                print(m)

    def write_packet_into_out_stream(self, packet_type, payload, sequence_num, payload_id):
        self.out_stream.seek(0)
        self.tmp_stream.seek(0)
        if packet_type != self.cmd_packet and packet_type != self.data_packet:
            self.logger("packet type error")
            return -1
        elif sequence_num > self.MAX_SEQUENCE_NUM:
            self.logger("sequence num error")
            return -1
        elif payload_id > self.MAX_PAYLOAD_ID:
            self.logger("payload id error")
            return -1
        else:
            msgpack.pack(payload, self.tmp_stream)
            payload_len = self.tmp_stream.tell()
            self.tmp_stream.seek(0)
            if payload_len > self.packet_size:
                self.logger(f"packet too long ({payload_len} bytes, limit is {self.packet_size})")
                return -1
            # header = (packet_type << 23) | (payload_len << 15) | sequence_num
            # Modified header
            header = (packet_type << 47) | (payload_len << 39) | (sequence_num << 20) | payload_id
            self.logger(f"header: {header}")
            self.logger(f"packet type: {packet_type}", f"payload len: {payload_len}",
                f"sequence num: {sequence_num}", f"payload ID: {payload_id}")
            self.logger(f"pycubed sending packet: {self.tmp_stream.getvalue()}")
            
            # Equivalent to header_arr = header.to_bytes(6, "big")
            header_arr = bytearray(6)
            header_arr[0] = (header >> 40) & 0xFF
            header_arr[1] = (header >> 32) & 0xFF
            header_arr[2] = (header >> 24) & 0xFF
            header_arr[3] = (header >> 16) & 0xFF
            header_arr[4] = (header >> 8) & 0xFF
            header_arr[5] = header & 0xFF
            self.out_stream.write(header_arr)
            self.out_stream.write(self.tmp_stream.read(payload_len))
            self.out_stream.seek(0)
            self.tmp_stream = io.BytesIO()  # TODO fix this.
            self.tmp_stream.seek(0)
            return payload_len

    def send_cmd_packet_sync(self, command):
        payload_len = self.write_packet_into_out_stream(
            self.cmd_packet, command, self.MAX_SEQUENCE_NUM, self.MAX_PAYLOAD_ID
        )
        if payload_len == -1:
            return False
        self.out_stream.seek(0)
        self.logger(f"wrote data: {self.out_stream.read(self.MAX_SIZE)}")
        self.out_stream.seek(0)
        success = self.protocol.send_with_ack(self.out_stream.read(self.MAX_SIZE))
        self.logger("waiting for ack...")
        if not success:
            self.logger("did not receive ack")
            return False
        self.logger("received ack")

    def send_data_packet_sync(self, payload, sequence_num=None, payload_id=None):
        if sequence_num is None:
            sequence_num = self.MAX_SEQUENCE_NUM
        if payload_id is None:
            payload_id = self.MAX_PAYLOAD_ID
        payload_len = self.write_packet_into_out_stream(
            self.data_packet, payload, sequence_num, payload_id
        )
        if payload_len == -1:
            return False
        self.out_stream.seek(0)
        self.logger(f"wrote data: {self.out_stream.read(self.MAX_SIZE)}")
        self.out_stream.seek(0)
        self.protocol.send(self.out_stream.read(self.MAX_SIZE))
        self.out_stream.seek(0)
        return True
    
    async def send_packet(self, packet):
        packet_type = packet.packet_type
        sequence_num = packet.sequence_num
        payload_id = packet.payload_id
        payload = packet.payload
        payload_len = self.write_packet_into_out_stream(
            packet_type, payload, sequence_num, payload_id
        )
        if payload_len == -1:
            return False
        # if packet_type == self.cmd_packet:
            # self.out_stream.seek(0)
            # self.logger(f"wrote data: {self.out_stream.read(self.MAX_SIZE)}")
            # self.out_stream.seek(0)
            # success = await self.protocol.send_with_ack(self.out_stream.read(self.MAX_SIZE))
            # self.logger("waiting for ack...")
            # if not success:
                # self.logger("did not receive ack")
                # return False
            # self.logger("received ack")
        # else:
            # self.out_stream.seek(0)
            # self.logger(f"wrote data: {self.out_stream.read(self.MAX_SIZE)}")
            # self.out_stream.seek(0)
            # self.protocol.send(self.out_stream.read(self.MAX_SIZE))
		
        # to do: acknowledge the right packets
        self.out_stream.seek(0)
        self.logger(f"wrote data: {self.out_stream.read(self.MAX_SIZE)}")
        self.out_stream.seek(0)
        self.protocol.send(self.out_stream.read(self.MAX_SIZE))
        self.out_stream.seek(0)
        return True
    
    
    async def receive_packet(self, with_ack=False):
        packet = self.protocol.receive(timeout=self.timeout, with_ack=with_ack) # Modified
        if packet is None:
            return AsyncPacketTransferProtocol.Packet(None, None, None, None)
        
        header = int.from_bytes(packet[0:6], "big")
        packet_type = header >> 47
        payload_len = (header >> 39) & (2**8 - 1)
        sequence_num = (header >> 20) & (2**19 - 1)
        payload_id = header & (2**20 - 1)
        self.logger(f"header: {header}")
        self.logger(f"packet type: {packet_type}", f"payload len: {payload_len}")
        self.logger(f"sequence num: {sequence_num}", f"payload ID: {payload_id}")
        self.tmp_stream = io.BytesIO()
        self.logger(f"tmp stream before rw: {self.tmp_stream.getvalue()}")
        self.tmp_stream.seek(0)
        self.tmp_stream.write(packet[6:]) # Modified
        self.logger(f"tmp stream before write: {self.tmp_stream.getvalue()}")
        self.tmp_stream.seek(0)
        self.logger(f"payload_packed: {self.tmp_stream.read(payload_len)}")
        self.tmp_stream.seek(0)
        try:
            payload = msgpack.unpack(self.tmp_stream)  # TODO make this the same?
        except TypeError:
            print(f"Unexpected structure: {self.tmp_stream.getvalue()}")
            return None
        except ValueError:
            print(f"Failed to decode: {self.tmp_stream.getvalue()}")
            return None
        except Exception as e:
            print(f"Unknown exception: {self.tmp_stream.getvalue()} {e}")
            return None
        else:
            # if packet_type == self.cmd_packet:
            #   print("pycubed sending ACK")
            #   self.protocol.send(b"ACK")
            self.tmp_stream = io.BytesIO()
            self.tmp_stream.seek(0)
            self.logger(f"payload: {payload}")
            return AsyncPacketTransferProtocol.Packet(packet_type, sequence_num, payload_id, payload)
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

