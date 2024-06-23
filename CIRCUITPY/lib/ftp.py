"""
`ftp`
====================================================

Simple CircuitPython compatible file transfer protocol
Modified for pycubed_rfm9x

* Author(s): 
 - Flynn Dreilinger

Implementation Notes
--------------------

"""
import os
import math
import time 
import asyncio

class FileTransferProtocol:

    def __init__(self, ptp, chunk_size=252, packet_delay=0, log=False):
        self.ptp = ptp
        self.log = log
        self.request_file_cmd = 's'
        self.request_partial_file_cmd = 'e'
        self.chunk_size = chunk_size # Modified
        self.packet_delay = packet_delay # Modified

    async def request_file(self, remote_path, local_path, retries=3):
        if self.log: print("PyCubed requesting file now")
        await self.ptp.send_packet(
            self.ptp.cmd_packet,
            [self.request_file_cmd, remote_path],
        )
        missing = await self.receive_file(local_path)
       
        while retries:
            if self.log: print(f"missing: {missing}")
            if self.log: print(f"retries remaining: {retries}")
            if missing == set():
                return True
            self.ptp.send_packet(
                self.ptp.cmd_packet,
                [self.request_partial_file_cmd, remote_path, list(missing)]
            )
            missing = await self.receive_partial_file(local_path, missing)
            retries -= 1
        return False
    
    async def receive_file(self, local_path):
        num_packets, sequence_number, payload_id = await self.ptp.receive_packet()
        num_packets = abs(num_packets)
        if self.log: print(f"expecting to receive {num_packets} packets")
        with open(local_path, 'ab+') as f:
            missing = {i for i in range(num_packets)}
            for packet_num in range(num_packets):
                chunk, packet_num_recvc, payload_id  = await self.ptp.receive_packet()
                missing.remove(packet_num_recvc)
                f.write(chunk)
                os.sync()
            return missing
    
    async def request_file_custom(self, remote_path, local_path, retries=3):
        # Request and handle_file
        return False
    
    async def handle_file(self, retries=3):
        packet_list, missing, file_id = await self.receive_file_custom()
        while retries > 0:
            if missing.count(1) == 0:
                return packet_list, missing, file_id
            if self.log: print(f"missing: {missing}, {retries} retries remaining")
            self.ptp.send_packet(
                self.ptp.cmd_packet,
                [self.request_partial_file_cmd, remote_path, missing]
            )
            missing = await self.receive_partial_file_custom(missing)
            retries -= 1
        return False
            
    
    async def receive_file_custom(self):
        # to do: store individual packets and assemble files when complete
        packet = await self.ptp.receive_packet()
        if packet.categorize() != "file_len":
            print(f"Packet of type {packet.categorize()} (not file_len) received")
            return None, None, None
        file_id = packet.payload_id
        num_packets = abs(packet.payload)
        if self.log:
            print(f"File {file_id} contains {num_packets} packets")
        packet_list = [None for i in range(num_packets)]
        missing = [1 for i in range(num_packets)]
        for packet_num in range(num_packets):
            packet = await self.ptp.receive_packet()
            if packet.categorize() != "file_data":
                print(f"Packet of type {packet.categorize()} (not file_data) received")
                continue
            chunk = packet.payload
            packet_num_recvc = packet.sequence_num
            packet_payload_id = packet.payload_id
            
            packet_list[packet_num_recvc] = chunk
            missing[packet_num_recvc] = 0
            if self.log:
                print(f"{missing.count(0)} packets of {num_packets} received")
        return packet_list, missing, packet_payload_id
    
    async def receive_partial_file_custom(self, missing):
        # Update missing with incoming packets
        return missing
    
    async def receive_file_sync(self, local_path):
        num_packets, sequence_number = self.ptp.receive_packet_sync()
        num_packets = abs(num_packets)
        if self.log: print(f"expecting to receive {num_packets} packets")
        with open(local_path, 'ab+') as f:
            missing = {i for i in range(num_packets)}
            for packet_num in range(num_packets):
                chunk, packet_num_recvc  = self.ptp.receive_packet_sync()
                missing.remove(packet_num_recvc)
                f.write(chunk)
                os.sync()
            return missing

    async def receive_partial_file(self, local_path, missing):
        _, _, _ = await self.ptp.receive_packet()
        missing_immutable = tuple(missing)
        for expected_packet_num in missing_immutable:
            chunk, recv_packet_num, payload_id  = await self.ptp.receive_packet()
            missing.remove(int(recv_packet_num))
            location = self.packet_size * recv_packet_num
            self.insert_into_file(chunk, local_path, location)
            os.sync()
        return missing

    def insert_into_file(self, data, filename, location):
        """Insert data into a file, and be worried about running out of RAM
        """
        with open(filename, 'rb+') as fh:
            fh.seek(location)
            with open('tmpfile', 'wb+') as th:
                for chunk, _ in self._read_chunks(fh, self.chunk_size): 
                    print(chunk)
                    th.write(chunk)
                fh.seek(location)
                fh.write(data)
        
        with open(filename, 'ab+') as fh:
            fh.seek(location + len(data))
            with open('tmpfile', 'rb+') as th:
                for chunk, _ in self._read_chunks(th, self.chunk_size): 
                    print(chunk)
                    fh.write(chunk)
        os.remove('tmpfile')

    async def send_file(self, filename, file_id=None):
        """Send a file

        Args:
            filename (str): path to file that will be sent
            chunk_size (int, optional): chunk sizes that will be sent. Defaults to 64.
        """
        with open(filename, 'rb') as f:
            stats = os.stat(filename)
            filesize = stats[6]
            
            # send the number of packets for the client
            print("Sending packet count and file ID")
            packet_count = math.ceil(filesize / self.chunk_size)
            packet = self.ptp.Packet.make_file_len(file_id, packet_count)
            await self.ptp.send_packet(packet)
            # await self.ptp.send_packet(
                # self.ptp.data_packet,
                 # - packet_count,
                # payload_id=file_id
            # )

            # send all the chunks
            for chunk, packet_num in self._read_chunks(f, self.chunk_size):
                if self.packet_delay > 0:
                    await asyncio.sleep(self.packet_delay)
                print(f"Sending packet {packet_num+1}")
                # success = await self.ptp.send_packet(
                    # self.ptp.data_packet,
                    # chunk,
                    # sequence_num=packet_num,
                    # payload_id=file_id
                # )
                packet = self.ptp.Packet.make_file_data(packet_num, file_id, chunk)
                success = await self.ptp.send_packet(packet)
                if not success:
                    print(f"Failed to send packet {packet_num}")
                else:
                    print(f"Packet {packet_num+1} of {packet_count} sent")

    def send_file_sync(self, filename, file_id=None):
        """Send a file

        Args:
            filename (str): path to file that will be sent
            chunk_size (int, optional): chunk sizes that will be sent. Defaults to 64.
        """
        with open(filename, 'rb') as f:
            stats = os.stat(filename)
            filesize = stats[6]
            
            # send the number of packets for the client
            print("sending number of packets!!!!!")
            self.ptp.send_data_packet_sync(
                 - math.ceil(filesize / self.chunk_size),
                payload_id=file_id
            )
            print("ok")

            # send all the chunks
            for chunk, packet_num in self._read_chunks(f, self.chunk_size):
                self.ptp.send_data_packet_sync(
                    chunk,
                    sequence_num=packet_num,
                    payload_id=file_id
                )
                
    def _read_chunks(self, infile, chunk_size):
        """Generator that reads chunks of a file

        Args:
            infile (str): path to file that will be read
            chunk_size (int, optional): chunk sizes that will be returned. Defaults to 64.

        Yields:
            bytes: chunk of file
        """
        counter = 0
        while True:
            chunk = infile.read(chunk_size)
            if chunk:
                yield (chunk, counter)
            else:
                break
            counter += 1

