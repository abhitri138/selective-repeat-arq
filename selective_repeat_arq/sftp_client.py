import queue
import socket
import sys
import time
import threading
import math

class Segment:
    def create(self, bytes, mss):
        self.seq_num = int(bytes[:32], 2)
        self.checksum = int(bytes[32:32+16])
        self.typeobj = int(bytes[32+16:32+16+16])
        return self

    def get(self, seq_num, data):
        seg = "{0:032b}".format(seq_num)
        seg += "{0:016b}".format(self.calculate_checksum(data))
        seg += "0101010101010101"
        seg = seg.encode()
        seg += data
        return seg

    def calculate_checksum(self, data):
        cs = 0
        if data is not None:
            for i in range(len(data)):
                cs = (cs + ((data[i] << 8) & 0xFF00)) if i % 2 == 0 else (cs + ((data[i]) & 0xFF))
                if len(data) % 2 != 0:
                    cs = cs + 0xFF

                while (cs >> 16) == 1:
                    cs = (cs & 0xFFFF) + (cs >> 16)
                    cs = ~cs
        return cs


class SftpClient:
    def __init__(self, server_host, file_name, window_size, MSS, server_port=7735, policy='go_back_n'):
        self.server_host = server_host
        self.server_port = int(server_port)
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.settimeout(0.8)
        self.server_address = (server_host, self.server_port)
        file = open(file_name, 'rb')
        self.data = file.read()
        self.window_size = int(window_size)
        self.MSS = int(MSS)
        self.data_size = int(MSS) - 64  # size of data in each segment
        self.TIMEOUT = 120
        self.window_free = self.window_size
        self.seq_num = 0
        self.lock = threading.Lock()
        self.last_ack_recv = -1
        self.TOTAL_PACKETS = math.ceil(len(self.data)/ self.data_size)
        self.dict = {}
        self.resend = {}
        if policy == 'selective_repeat':
            self.policy = self.selective_repeat
        else:
            self.policy = self.rdt_send
        
    def start(self):
        # try:
        ack_thread = threading.Thread(target=self.selective_arq)
        t = time.time()
        ack_thread.start()

        self.policy()
        t = time.time() - t
        print("Time to transfer: ", t)
        return t



    def rdt_send(self):

        while self.last_ack_recv < self.TOTAL_PACKETS:
            while self.seq_num * self.data_size < len(self.data) and self.window_free:
                data_start = self.seq_num * self.data_size
                data_end = data_start + self.data_size
                data = self.data[data_start:data_end]
                dg = Segment().get(self.seq_num, data)
                self.server_sock.sendto(dg, self.server_address)
                self.lock.acquire()
                self.dict[self.seq_num] = dg
                self.seq_num += 1
                self.window_free -= 1
                self.lock.release()

            for key in self.resend.keys():
                data = self.resend[key]
                dg = Segment().get(key, data)
                self.server_sock.sendto(dg, self.server_address)

    def selective_arq(self):
        while self.last_ack_recv < self.TOTAL_PACKETS:
            try:

                ack, server = self.server_sock.recvfrom(1024)  # check buffersize
                ack_dg = Segment().create(ack, self.MSS)
                if ack_dg.seq_num >= self.last_ack_recv:
                    self.lock.acquire()
                    self.last_ack_recv = ack_dg.seq_num
                    self.window_free += self.seq_num % self.window_size
                    if self.window_free > self.window_size:
                        self.window_free = self.window_size
                    self.lock.release()
                else:
                    self.resend[ack_dg.seq_num] = self.dict[ack_dg.seq_num]

            except Exception as e:
                if e.args[0] != 'timed out':
                    print(e)
                if self.last_ack_recv != -1:
                    self.lock.acquire()
                    self.window_free = self.window_size
                    self.seq_num = self.last_ack_recv
                    print("Timeout, sequence number = ", self.seq_num)
                    self.lock.release()

    def selective_repeat(self):
        return


def main(server_host, server_port, file_name, window_size, MSS):
    client = SftpClient(server_host=server_host, server_port=server_port, file_name=file_name,
                        window_size=window_size, MSS=MSS)
    return client.start()


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 5:
        print("Not Enough Args passed!!")
        exit()
    server_host = args[0]
    server_port = args[1]
    file_name = args[2]
    window_size = args[3]
    MSS = args[4]
    main(server_host, server_port, file_name, window_size, MSS)
