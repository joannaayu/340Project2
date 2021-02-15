# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
#import struct needed for send function
from struct import *
#import for background listening
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

import hashlib
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

        #sequence numbers for implementing Nagle's Algorithm
        self.seq_num = 2

        self.recv_num = 2
        self.fin_num = 1

        #used for fin and ack flags
        # self.fin_num = 0
        # self.ack_num = 0

        #receive buffer
        self.r_buff = {}

        self.closed = False

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

        while len(data_bytes) > 1452:

            self.r_buff = {}
            # header = pack('i', 0) + pack('i', 0) + pack('i', self.seq_num)
            header = pack('i', self.seq_num)
            hash = hashlib.md5(pack('i', self.seq_num) + data_bytes[0:1452])
            digested_hash = hash.digest()
            #print(digested_hash)
            sbytes = digested_hash + header + data_bytes[0:1452]
            data_bytes = data_bytes[1452:]

            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

            self.ack = False
            time.sleep(.25)

            while self.ack != True:
                time.sleep(.25)
                if self.ack == False:
                    self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

                else:
                    break


            self.seq_num = self.seq_num + 1
            # self.s_buff[self.seq_num] = sbytes

        header = pack('i', self.seq_num)
        hash = hashlib.md5(pack('i', self.seq_num) + data_bytes)
        digested_hash = hash.digest()
        #print('DIGESTED HASH IN SEND', digested_hash)
        sbytes = digested_hash + header + data_bytes
        #print('SBYTES BEFORE SEND', sbytes)
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


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        while True:
            #can be while loop too

            if self.recv_num in self.r_buff:

                data = self.r_buff[self.recv_num]
                #cleans up the r_buff after packet is sent to instance 1
                self.r_buff.pop(self.recv_num)
                self.recv_num += 1
                return data



    def listener(self):
        #code taken from the project page so far
        while not self.closed:
            try:

                data, addr = self.socket.recvfrom()

                if len(data) == 0:
                    return

                hash_check = data[0:16]
                #print('HASH CHECK IN LISTENER', hash_check)


                # fin_header = unpack('i', data[16:20])[0]
                # ack_header = unpack('i', data[20:24])[0]
                recv_header = unpack('i', data[16:20])[0]

                digested_data = hashlib.md5(data[16:]).digest()
                #print('DIGESTED DATA', digested_data)

                if recv_header == 1:
                    if hash_check == digested_data:
                        header = pack('i', -1)
                        recv_header = -1
                        hash = hashlib.md5(pack('i', recv_header)).digest()
                        fin_ack_pack = hash + header
                        self.fin = True
                        self.finack = True

                        self.socket.sendto(fin_ack_pack, (self.dst_ip, self.dst_port))
                        print('SENDING FINACK')

                    #print('HASH SUCCESS IN FIN CHECK', hash_check, digested_data)
                        # if ack_header == 0:
                        #     if hash_check == digested_data:
                        #         #print('HASH SUCCESS IN FINACK', hash_check, digested_data)
                        #         header = pack('i', 1) + pack('i', 1) + pack('i', recv_header)
                        #         ack_header = 1
                        #         hash = hashlib.md5(pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)).digest()
                        #         fin_ack_pack = hash + header
                        #         self.fin = True
                        #         self.finack = True
                        #
                        #         self.socket.sendto(fin_ack_pack, (self.dst_ip, self.dst_port))
                        #         print('SENDING FINACK')

                elif recv_header == -1:
                    if hash_check == digested_data:
                        # print('HASH SUCCESS IN RECEIVING FINACK', hash_check, digested_data)
                        print('FINACK RECV')
                        self.finack = True
                        self.fin = True
                        self.close()

                elif recv_header > 0:
                    if hash_check == digested_data:
                        #print('HASH SUCCESS IN SECOND ELIF', hash_check, digested_data)
                        data = data[20:]
                        self.r_buff[recv_header] = data

                        # ack_header = 1
                        self.ack = True

                        recv_header = (-1 * recv_header)

                        header = pack('i', recv_header)
                        hash = hashlib.md5(pack('i', recv_header)).digest()
                        packet_ack = hash + header
                        self.socket.sendto(packet_ack, (self.dst_ip, self.dst_port))

                    #print('ack sent', recv_header, self.ack)

                elif recv_header < 0:
                    if hash_check == digested_data:
                        self.ack = True
                        print('ack recv', recv_header, self.ack)


            except Exception as e:
                print("listener died, uh o!")
                print(e)

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.

        if self.fin == False:

            fin_header = pack('i', self.fin_num)
            fin_hash = hashlib.md5(pack('i', self.fin_num)).digest()
            fin_pack = fin_hash + fin_header

            self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))
            self.finack = False

            time.sleep(.25)

            if self.finack == True:
                print('FINACK RECV')

            while self.finack == False:
                time.sleep(.25)

                if self.finack == False:
                    self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))

                else:
                    break

        elif self.fin and self.finack == True:
            print('CLOSE SUCCESS -----')
            time.sleep(2)
            self.closed = True
            self.socket.stoprecv()
            return
