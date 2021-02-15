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
from threading import Timer


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

        #receive buffer
        self.r_buff = {}

        #buffer of non ACKed packets
        self.broken_packets = {}

        self.closed = False

        #checks for our fin ack
        self.fin = False
        self.finack = False

        self.ack = False

        self.last_packet = 0

        #creating an executor with max (2) thread
        executor = ThreadPoolExecutor(max_workers=1)
        #submits a task
        executor.submit(self.listener)
        print("created executor!")

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        #if self.last_packet == re
        while len(data_bytes) > 1444:
            self.r_buff = {}
            header = pack('i', 0) + pack('i', 0) + pack('i', self.seq_num)
            hash = hashlib.md5(pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num) + data_bytes[0:1444])
            digested_hash = hash.digest()
            #print(digested_hash)
            sbytes = digested_hash + header + data_bytes[0:1444]
            self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))

            self.ack = False
            # time.sleep(.25)
            #
            # while self.ack != True:
            #     time.sleep(.25)
            #     if self.ack == False:
            #         self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
            #
            #     else:
            #         break

            data_bytes = data_bytes[1444:]
            #packed_seq = pack('i', self.seq_num)
            self.broken_packets[self.seq_num] = sbytes
            Timer(0.25, self.resend, [pack('i', self.seq_num)]).start()
            self.seq_num = self.seq_num + 1

        header = pack('i', 0) + pack('i', 0) + pack('i', self.seq_num)
        hash = hashlib.md5(pack('i', self.fin_num) + pack('i', self.ack_num) + pack('i', self.seq_num) + data_bytes)
        digested_hash = hash.digest()
        #print('DIGESTED HASH IN SEND', digested_hash)
        sbytes = digested_hash + header + data_bytes
        #print('SBYTES BEFORE SEND', sbytes)
        self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        self.broken_packets[self.seq_num] = sbytes
        #packed_seq = pack('i', self.seq_num)
        Timer(0.25, self.resend, [pack('i', self.seq_num)]).start()
        self.seq_num = self.seq_num + 1
        self.ack = False

        # time.sleep(.25)
        #
        # while not self.ack:
        #     time.sleep(.25)
        #     if self.ack == False:
        #         self.socket.sendto(sbytes, (self.dst_ip, self.dst_port))
        #     else:
        #         break


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

    # def sendACK(self, d_bytes: bytes):
    #     try:
    #         hash = hashlib.md5(d_bytes).digest()
    #         self.socket.sendto(hash + d_bytes, (self.dst_ip, self.dst_port))
    #     except:
    #         print('error in sendACK oops')

    def listener(self):
        #code taken from the project page so far
        while not self.closed:
            try:

                data, addr = self.socket.recvfrom()


                hash_check = data[0:16]
                #print('HASH CHECK IN LISTENER', hash_check)

                fin_header = unpack('i', data[16:20])[0]
                ack_header = unpack('i', data[20:24])[0]
                recv_header = unpack('i', data[24:28])[0]

                digested_data = hashlib.md5(data[16:]).digest()
                #print('DIGESTED DATA', digested_data)

                if fin_header == 1:
                    if ack_header == 0:
                        if hash_check == digested_data:
                            print('FIN CASE, DATA IS', fin_header, ack_header, recv_header, self.fin, self.finack)
                            header = pack('i', 1) + pack('i', 1) + pack('i', recv_header)
                            ack_header = 1
                            hash = hashlib.md5(pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)).digest()
                            fin_ack_pack = hash + header
                            self.fin = True
                            self.finack = True
                            #del self.broken_packets[recv_header]
                            #self.broken_packets.pop(recv_header)

                            print('LAST PACKET AND RECV HEADER', self.last_packet, recv_header)
                            #print('last seq_num', self.last_packet)
                            # print('in the fin case')

                            if self.last_packet == (recv_header - 1):

                                print('SENDING FINACK', fin_header, ack_header, recv_header, self.fin, self.finack)
                                #Timer(.05, self.sendACK, [fin_pack]).start()
                                self.socket.sendto(fin_ack_pack, (self.dst_ip, self.dst_port))

                                # print(fin_header, ack_header, recv_header)
                                # print('sending recv header', recv_header)
                                # print('sending last seq_num', self.last_packet)

                elif fin_header == 1:
                    if ack_header == 1:
                        print('FINACK DETECTED', fin_header, ack_header, recv_header, self.fin, self.finack)
                        if hash_check == digested_data:
                            #print('HASH SUCCESS IN RECEIVING FINACK', hash_check, digested_data)
                            #self.finack = True
                            if recv_header in self.broken_packets:
                                self.broken_packets.pop(recv_header)
                            print('RECV FINACK', fin_header, ack_header, recv_header)
                            self.finack = True
                            self.fin = True
                            self.close()

                elif fin_header == 0 and ack_header == 0:
                    if hash_check == digested_data:
                        #print('HASH SUCCESS IN SECOND ELIF', hash_check, digested_data)
                        data = data[28:]
                        self.r_buff[recv_header] = data

                        self.last_packet = max(recv_header, self.last_packet)

                        ack_header = 1
                        self.ack = True

                        header = pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)
                        hash = hashlib.md5(pack('i', fin_header) + pack('i', ack_header) + pack('i', recv_header)).digest()
                        packet_ack = hash + header
                        self.socket.sendto(packet_ack, (self.dst_ip, self.dst_port))
                        #Timer(.5, self.sendACK, [packet_ack]).start()

                        # print('ack sent', recv_header)
                        print('SENDING ACK', fin_header, ack_header, recv_header)

                elif fin_header == 0 and ack_header == 1:
                    if hash_check == digested_data:
                        #self.last_packet = max(recv_header, self.last_packet)
                        #print('HASH SUCCESS IN LAST ELIF', hash_check, digested_data)
                        self.ack = True
                        #print('ack recv', recv_header, self.ack)
                        if recv_header in self.broken_packets:
                            self.broken_packets.pop(recv_header)
                        print('RECV ACK', fin_header, ack_header, recv_header, self.fin, self.finack)
                        #self.broken_packets.pop(recv_header)


            except Exception as e:
                print("listener died, uh o!")
                print(e)

    def resend(self, d_bytes: bytes) -> None:
        recv_header = unpack('i', d_bytes)[0]

        if recv_header in self.broken_packets:
            print('in our buffer', recv_header)

        if recv_header not in self.broken_packets:
            print('not found in buffer2', recv_header)

        while recv_header in self.broken_packets:
            #print(self.broken_packets)
            try:
                print('now resending packet', recv_header)
                self.socket.sendto(self.broken_packets[recv_header], (self.dst_ip, self.dst_port))

            except Exception as e:
                print("resend failed, uh o!")
                print(e)

            # if recv_header not in self.broken_packets:
            #     return
            else:
                time.sleep(0.25)
                #Timer(.25, self.resend, [d_bytes]).start()
        #print(self.broken_packets)
        #print('in resend function', recv_header)
        #
        # if recv_header not in self.broken_packets:
        #     #print('%s packet popped' % (recv_header))
        #     return

        # if recv_header in self.broken_packets:
        #     self.socket.sendto(d_bytes, (self.dst_ip, self.dst_port))
        #
        #     if recv_header in self.broken_packets:
        #         Timer(.25, self.resend, [d_bytes]).start()
        #
        #     else:
        #         return


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.

        if self.fin == False:
            #print('Attempting to close')
            fin_header = pack('i', 1) + pack('i', 0) + pack('i', self.seq_num)
            fin_hash = hashlib.md5(pack('i', 1) + pack('i', 0) + pack('i', self.seq_num)).digest()
            fin_pack = fin_hash + fin_header
            #print('CLOSE SEQ NUM', self.seq_num)
            self.broken_packets[self.seq_num] = fin_pack
            self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))
            self.fin = True
            self.finack = False

            Timer(0.25, self.resend, [pack('i', self.seq_num)]).start()

            #time.sleep(.25)

            # if self.finack == True:
            #     print('FINACK RECV')
            #
            # while self.finack == False:
            #     time.sleep(.25)
            #
            #     if self.finack == False:
            #         self.socket.sendto(fin_pack, (self.dst_ip, self.dst_port))
            #         print('sending finack again, wasnt recieved')
            #
            #     else:
            #         break

        elif self.fin and self.finack == True:
            print('CLOSE SUCCESS -----')
            time.sleep(2)
            self.closed = True
            self.socket.stoprecv()
            return
