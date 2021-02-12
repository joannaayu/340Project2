# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
#import struct needed for send function
from struct import *
#import for background listening
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor


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
        self.s_buff = {}

        self.closed = False

        #creating an executor with max (2) thread
        executor = ThreadPoolExecutor(max_workers=1)
        #submits a task
        executor.submit(self.listener)
        print("created executor!")

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!

        while len(data_bytes) > 1468:
            header = pack('i', self.seq_num)
            sbytes = header + data_bytes[0:1468]
            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
            self.s_buff[self.seq_num] = sbytes
            data_bytes = data_bytes[1468:]

            self.seq_num = self.seq_num + 1
            #self.s_buff[self.seq_num] = sbytes

        header = pack('i', self.seq_num)
        #print(header)
        sbytes = header + data_bytes
        #print(sbytes)
        self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        self.s_buff[self.seq_num] = sbytes
        self.seq_num = self.seq_num + 1
        #print('packet num check', self.seq_num, data_bytes[0:1468], 'stored in sbytes', sbytes)



    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        while True:
            #can be while loop too
            if self.recv_num in self.r_buff:
                #print('IN OUR RECV FUNC', self.recv_num, 'CURR R_BUFF IS:', self.r_buff)
                data = self.r_buff[self.recv_num]
                #cleans up the r_buff after packet is sent to instance 1
                del self.r_buff[self.recv_num]
                self.recv_num += 1

                return data

            # data, addr = self.socket.recvfrom(1472)
            # recv_header = unpack('i', data[0:4])[0]
            # #print(recv_header)
            # data = data[4:]
            # self.r_buff[recv_header] = data
            #print(self.r_buff)

    def listener(self):
        #code taken from the project page so far
        while not self.closed:
            try:
                data, addr = self.socket.recvfrom()
                recv_header = unpack('i', data[0:4])[0]
                #print('HEADER IS', recv_header)
                data = data[4:]
                #print('DATA IS', data)
                #self.r_buff[recv_header] = data
                # print(addr)
                #r_buff{data} = data

                #check if ACK or data
                if recv_header > 0:
                    #print('NEW DATA IS', data)
                    self.r_buff[recv_header] = data
                    #print('RBUFF IS', self.r_buff)

                elif recv_header < 0:
                    check_header = recv_header * -1
                    if check_header in self.s_buffer:
                        self.s_buffer.pop(check_header)


            except Exception as e:
                print("listener died, uh o!")
                print(e)



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.closed = True
        self.socket.stoprecv()
