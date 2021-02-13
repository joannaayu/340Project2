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

import hashlib





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
        self.s_buff = {}
        self.r_buff = {}
        self.s_buff = {}


        #checks for our final fin packet
        self.fin = False
        self.finack = False

        self.closed = False
        self.ack = False

        #self.last_packet = 0

        #creating an executor with max (2) thread
        executor = ThreadPoolExecutor(max_workers=1)
        #submits a task
        executor.submit(self.listener)
        print("created executor!")

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!


        while len(data_bytes) > 1444:
            header = pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num)
            hash = hashlib.md5(pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num) + data_bytes[0:1444])
            digested_hash = hash.digest()
            sbytes = digested_hash + header + data_bytes[0:1444]
            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

            self.s_buff[self.seq_num] = sbytes

            data_bytes = data_bytes[1444:]

            self.seq_num = self.seq_num + 1
            self.s_buff[self.seq_num] = sbytes

        header = pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num)
        hash = hashlib.md5(pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num) + data_bytes)
        digested_hash = hash.digest()
        sbytes = digested_hash + header + data_bytes
        self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        self.s_buff[self.seq_num] = sbytes
        self.seq_num = self.seq_num + 1

        # r = Timer(10, self.resend, sbytes)
        self.ack = False

        time.sleep(.25)

        while self.ack != True:
            time.sleep(.25)

            if self.ack == False:
                self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
            else:
                break

        if self.seq_num == 1000:
            while not self.ack:
                time.sleep(.01)


    # def resend(self, data_bytes: bytes) -> None:
    #
    #     try:
    #         print('sending in resend')
    #         print(self.ack)
    #         print(self.ack_num)
    #
    #         self.socket.sendto(data_bytes, (self.dst_ip, self.dst_port))
    #
    #     except:
    #         print("EROOROROORO: cnat resend")
    #         return



        # else:
        #     print('in else case')
        #     time.sleep(.25)
        #     self.resend(data_bytes)


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

                hash_check = data[0:16]

                fin_header = unpack('i', data[16:20])[0]
                ack_header = unpack('i', data[20:24])[0]
                recv_header = unpack('i', data[24:28])[0]


                # print(fin_header)
                # print(ack_header)
                # print(recv_header)

                data_digested = hashlib.md5(data[28:]).digest()

                self.r_buff[recv_header] = data

                #if our fin bit is set we know its the last packet
                if fin_header == 1:
                    if data_digested == hash_check:
                    #check if we have sent the ack for the fin packet, if not set the ack bit
                    print('CURR ACK STATE IS', ack_header)
                        if ack_header == 0:
                            header = pack('i', 1) + pack('i', 1) + pack('i', recv_header)
                            print('FIN SENDING, SETTING FIN AND ACK BIT TO', unpack('i', header[4:8][0]))
                            self.fin = True

                            try:
                                self.socket.sendto(data, (self.dst_ip, self.dst_port))
                            except:
                                print('error sending fin ack')

                        #fin sent, fin ack recieved, time to close
                        else:
                            print('FINACK GUD, ATTEMPT TO CLOSE!-----------')
                            self.finack = True
                            self.close()

                elif ack_header == 0:
                    if data_digested == hash_check:
                        ack_header = 1
                        self.ack = True
                        header = pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)

                        self.socket.sendto(header, (self.dst_ip, self.dst_port))

                        # print('ack sent')
                        # print(self.ack)

                        # except:
                        #     print("error sending ack")

                elif ack_header == 1:
                    if data_digested == hash_check:

                        self.ack = True
                        # print("This is listener ack", self.ack)

                        # self.ack = True
                        # print('ack recv', recv_header)
                        #self.last_packet = max(recv_header, self.lastpacket)

                        # if recv_header in self.s_buff:
                        #     hello = self.s_buff[recv_header]
                        #
                        #     self.s_buff.pop(recv_header)
            except Exception as e:
                print("listener died, uh o!")
                print(e)


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        if self.fin == False:
            fin_header = pack('i', 1) + pack('i', 0) + pack('i', self.seq_num)
            fin_hash = hashlib.md5(pack('i', 1) + pack('i', 0) + pack('i', self.seq_num))
            fin_pack = fin_header + fin_hash

            print(self.seq_num)
            self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))

            self.finack = False
            ack_counter = 0
            time.sleep(.25)

            if self.finack == True:
                print('FINACK RECV')

            while self.finack == False:
                time.sleep(.25)

                if self.finack == False:
                    self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))
                    ack_counter += 1
                    print('IN OUR FINACK LOOP', ack_counter)

                else:
                    break

        elif self.fin == True and self.finack == True:
            print('CLOSED SUCCESS')
            time.sleep(2)
            self.closed = True
            self.socket.stoprecv()
            self.socket.close()
            return
