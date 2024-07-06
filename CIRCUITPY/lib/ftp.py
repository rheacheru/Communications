"""
Irvington CubeSat's file transfer protocol for CircuitPython
Inspired by `ftp` from Stanford PyGS
"""
from os import mkdir, listdir, stat
from time import monotonic
from asyncio import sleep
from icpacket import Packet

class FileTransferProtocol:

    def __init__(self, ptp, chunk_size=252, packet_delay=0, request_size=10, log=False):
        self.ptp = ptp
        self.log = log
        self.request_file_cmd = 's'
        self.request_partial_file_cmd = 'e'
        self.chunk_size = chunk_size # Modified
        self.packet_delay = packet_delay # Modified
        
        try:
            if request_size > 48:
                print("Warning: Request size should not exceed 48 on PyCubed")
        except:
            print("Warning: Request size not int")
        self.request_size = request_size

    
    
    async def _request_partial(self, file_id, missing):
        request = []
        for i in range(len(missing)):
            if missing[i] == 1:
                request.append(i)
                if len(request) == self.request_size: # Request at most request_size packets
                    break
        packet = Packet.make_file_req(file_id, request)
        await self.ptp.send_packet(packet)
        return len(request)
        
    
    async def request_file_custom(self, file_id, filename, local_path, retry_limit=None, defer_assembly=False):
        '''
        Request the file specified by its unique file_id, storing it as filename.
        The local_path directory is used to store packets, metadata, and the complete file.
        '''
        # Make local_path directory
        try:
            mkdir(local_path)
        except:
            pass
        
        if retry_limit is None: retry_limit = float("inf")
        retries = 0
        
        # Get packet count and packet status and send the first request
        # State: num_packets, missing, waiting_on
        if "packet_status.txt" in listdir(local_path): # file has been requested before
            with open(f"{local_path}/packet_status.txt") as f:
                num_packets = int(f.readline())
                missing = list(map(int, f.readline().strip()))
            if missing.count(1) == 0:
                print(f"File {file_id} has no missing packets")
                return True
            
            print(f"Requesting part of file {file_id}, {missing}")
            waiting_on = await self._request_partial(file_id, missing)
        
        else: # file has not been requested before
            packet = Packet.make_file_req(file_id) # request all
            print(f"Requesting all of file {file_id}")
            await self.ptp.send_packet(packet)
            
            header_packet = await self.ptp.receive_packet()
            if header_packet.categorize() != "file_len":
                print(f"Packet of type {header_packet.categorize()} (not file_len) received")
                return False
            
            assert header_packet.payload_id == file_id, "File IDs don't match"
            num_packets = abs(header_packet.payload)
            if self.log:
                print(f"File {file_id} contains {num_packets} packets")
            missing = [1]*num_packets
            waiting_on = num_packets
        
        # Receive file data
        while True:
            received_packets = await self.receive_file_custom(waiting_on, local_path)
            
            # to do: replace this with a check for no acknowledgement of the request
            if len(received_packets) == 0:
                print("No response to request, ending attempts")
                return False
            
            # Update missing
            for rec in received_packets:
                missing[rec] = 0
            
            # Update packet status
            with open(f"{local_path}/packet_status.txt", "w") as f:
                f.write(str(num_packets))
                f.write("\n")
                f.write(''.join(map(str, missing)))
            
            if missing.count(1) == 0: # All packets received
                if not defer_assembly:
                    # Assemble file
                    with open(f"{local_path}/{filename}", "wb") as f:
                        for i in range(num_packets):
                            with open(f"{local_path}/packet_{i}", "rb") as g:
                                f.write(g.read(self.chunk_size))
                if self.log: print(f"File {file_id} has been completely received")
                return True
            
            # Not all packets received
            if retries >= retry_limit:
                print(f"Retry limit reached ({retry_limit})")
                return False
            retries += 1
            if self.log: print(f"missing: {missing}, requesting partial (attempt {retries})")
            waiting_on = await self._request_partial(file_id, missing)
    
    async def receive_file_custom(self, incoming_packets, local_path, timeout=10):
        received_packets = []
        last_time = monotonic()
        for packet_num in range(incoming_packets):
            packet = await self.ptp.receive_packet()
            if packet.categorize() != "file_data":
                print(f"Packet of type {packet.categorize()} (not file_data) received")
                if monotonic() - last_time >= timeout:
                    print(f"No valid packets received in the past {timeout} seconds, breaking")
                    break
                continue
            
            # Packet received
            last_time = monotonic()
            with open(f"{local_path}/packet_{packet.sequence_num}", "wb") as f:
                f.write(packet.payload)
            received_packets.append(packet.sequence_num)
            if self.log:
                print(f"Packet {packet.sequence_num} received ({len(received_packets)}/{incoming_packets})")
        return received_packets
    
    def assemble_file(self, filename, local_path):
        """
        Assemble the packets stored at local_path and store as local_path/filename.
        To be used when requesting files with defer_assembly=True
        """
        with open(f"{local_path}/packet_status.txt") as f:
            num_packets = int(f.readline())
            missing = list(map(int, f.readline().strip()))
        assert missing.count(1) == 0, "File has missing packets"
        with open(f"{local_path}/{filename}", "wb") as f:
            for i in range(num_packets):
                with open(f"{local_path}/packet_{i}", "rb") as g:
                    f.write(g.read(self.chunk_size))
        return True
    
    
    
    async def send_partial_file(self, filename, file_id, request):
        with open(filename, "rb") as f:
            for packet_num in request:
                if self.packet_delay > 0:
                    await sleep(self.packet_delay)
                print(f"Sending packet {packet_num+1}")
                f.seek(self.chunk_size * packet_num)
                chunk = f.read(self.chunk_size)
                packet = Packet.make_file_data(packet_num, file_id, chunk)
                success = await self.ptp.send_packet(packet)
                if not success:
                    print(f"Failed to send packet {packet_num+1}")
                else:
                    print(f"Packet {packet_num+1} sent")
    
    async def send_file(self, filename, file_id):
        """Send a file

        Args:
            filename (str): path to file that will be sent
            chunk_size (int, optional): chunk sizes that will be sent. Defaults to 64.
        """
        with open(filename, 'rb') as f:
            filesize = stat(filename)[6]
            
            # send the number of packets for the client
            print("Sending packet count and file ID")
            packet_count = (filesize-1) // self.chunk_size + 1 # ceil
            packet = Packet.make_file_len(file_id, packet_count)
            await self.ptp.send_packet(packet)

            # send all the chunks
            for chunk, packet_num in self._read_chunks(f, self.chunk_size):
                if self.packet_delay > 0:
                    await sleep(self.packet_delay)
                print(f"Sending packet {packet_num+1}")
                packet = Packet.make_file_data(packet_num, file_id, chunk)
                success = await self.ptp.send_packet(packet)
                if not success:
                    print(f"Failed to send packet {packet_num+1}")
                else:
                    print(f"Packet {packet_num+1} of {packet_count} sent")

    
                
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

