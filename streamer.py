# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY

from struct import *

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

        #sequence numbers
        self.seq_num = 0
        self.recv_num = 0

        #send & receive buffers
        #self.s_buff = {}
        self.r_buff = {}

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!

        while len(data_bytes) > 1468:
            header = pack('i', self.seq_num)
            sbytes = header + data_bytes[0:1468]
            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
            data_bytes = data_bytes[1468:]

            self.seq_num = self.seq_num + 1

            #self.s_buff[self.seq_num] = sbytes

        header = pack('i', self.seq_num)
        sbytes = header + data_bytes
        self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        self.seq_num = self.seq_num + 1


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        while True:

            #can be while loop too
            if self.recv_num in self.r_buff:

                data = self.r_buff[self.recv_num]
                # dont technically need this
                # del self.r_buff[self.recv_num]
                self.recv_num += 1

                return data

            data, addr = self.socket.recvfrom(1472)
            recv_header = unpack('i', data[0:4])[0]
            data = data[4:]
            self.r_buff[recv_header] = data


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
