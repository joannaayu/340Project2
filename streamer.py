# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
#import struct needed for send function
from struct import *
#import for background listening
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

import time





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


        self.fin_num = 0
        self.ack_num = 0

        #send & receive buffers
        # self.s_buff = {}
        self.r_buff = {}


        self.closed = False

        #
        self.fin = False
        self.finack = False


        self.ack = False

        #creating an executor with max (2) thread
        executor = ThreadPoolExecutor(max_workers=1)
        #submits a task
        executor.submit(self.listener)
        print("created executor!")

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!




        while len(data_bytes) > 1460:

            print('in sending while loop seqnum', self.seq_num)

            header = pack('i', 0) + pack('i', 0) + pack('i', self.seq_num)
            sbytes = header + data_bytes[0:1460]

            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

            self.ack = False
            time.sleep(.25)
            print('in sending while loop ack', self.ack)

            while self.ack != True:
                print('in TIMEOUT while loop ack', self.ack)

                time.sleep(.25)

                if self.ack == False:
                    self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

                else:
                    break

            # self.s_buff[self.seq_num] = sbytes
            data_bytes = data_bytes[1460:]
            self.seq_num = self.seq_num + 1

                # self.s_buff[self.seq_num] = sbytes


        header = pack('i', 0) + pack('i', 0) + pack('i', self.seq_num)
        sbytes = header + data_bytes

        self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        # self.s_buff[self.seq_num] = sbytes
        self.seq_num = self.seq_num + 1

        self.ack = False

        time.sleep(.25)

        while not self.ack:
            time.sleep(.25)
            if self.ack == False:
                self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
            else:
                break


        if self.seq_num == 999:
            while not self.ack:
                time.sleep(.01)


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        while True:
            #can be while loop too
            if self.recv_num in self.r_buff:

                data = self.r_buff[self.recv_num]
                #cleans up the r_buff after packet is sent to instance 1
                del self.r_buff[self.recv_num]
                self.recv_num += 1

                return data


    def listener(self):
        #code taken from the project page so far
        while not self.closed:
            try:

                data, addr = self.socket.recvfrom()

                fin_header = unpack('i', data[0:4])[0]
                ack_header = unpack('i', data[4:8])[0]
                recv_header = unpack('i', data[8:12])[0]

                # print(fin_header)
                # print(ack_header)
                # print(recv_header)

                data = data[12:]

                self.r_buff[recv_header] = data

                if fin_header == 1:
                    if ack_header == 0:
                        header = pack('i', 1) + pack('i', 1) + pack('i', recv_header)

                        print ('in fin listener', recv_header)
                        self.fin = True
                        self.finack = True

                        self.socket.sendto(header, (self.dst_ip, self.dst_port))

                    else:
                        print('finack recv')
                        self.finack = True
                        self.fin = True
                        self.close()

                elif fin_header == 0 and ack_header == 0:
                    ack_header = 1
                    self.ack = True

                    header = pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)
                    self.socket.sendto(header, (self.dst_ip, self.dst_port))

                    print('ack sent', recv_header, self.ack)

                elif fin_header == 0 and ack_header == 1:
                    self.ack = True
                    print('ack recv', recv_header, self.ack)


            except Exception as e:
                print("listener died, uh o!")
                print(e)

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        print('in close self.fin', self.fin)
        print('in close self.finack', self.finack)

        if self.fin == False:
            print("in close", self.seq_num)
            fin_header = pack('i', 1) + pack('i', 0) + pack('i', self.seq_num)
            self.socket.sendto(fin_header, (self.dst_ip, self.dst_port))
            self.finack = False

            ack_counter = 0
            time.sleep(.25)

            if self.finack == True:
                print('FINACK RECV')

            while self.finack == False:
                time.sleep(.25)

                if self.finack == False:
                    self.socket.sendto(fin_header, (self.dst_ip, self.dst_port))
                    ack_counter = ack_counter + 1
                    print("times in our finack loop is", ack_counter)
                else:

                    break

        elif self.fin and self.finack == True:
            print('CLOSE SUCCESS -----')
            time.sleep(2)
            self.closed = True
            self.socket.stoprecv()
            return
