import hashlib
import socket
import sys
import time


class Segment:
    # def __init__(self, seq_num, mss):
    #     self.seq_num = seq_num
    #     self.checksum = int(bytes[32:32+16])
    #     self.typeobj = int(bytes[32+16:32+16+16])
    #     self.data = bytes[32+16+16:mss].decode()

    def get(self, seq_num, data):
        seg = "{0:032b}".format(seq_num)
        seg += "{0:016b}".format(self.calculate_checksum(data))
        seg += "0101010101010101"
        seg = seg.encode()
        seg += data
        return seg

    def calculate_checksum(self,data):
        return 100


class SftpClient:
    def __init__(self, server_host, file_name, window_size, MSS, server_port=7735, policy='go_back_n'):
        self.server_host = server_host
        self.server_port = int(server_port)
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (server_host, self.server_port)
        file = open(file_name, 'rb')
        self.data = file.read()
        self.window_size = int(window_size)
        self.MSS = int(MSS)
        self.data_size = int(MSS) - 64  # size of data in each segment
        self.TIMEOUT = 120
        if policy == 'selective_repeat':
            self.policy = self.selective_repeat
        else:
            self.policy = self.rdt_send

    def start(self):
        try:
            self.policy()
        finally:
            self.server_sock.close()

    def rdt_send(self):
        seq_num = 0
        window_free = self.window_size
        counters = []
        last_ack_recv = -1
        while seq_num * self.data_size < len(self.data):
            while window_free:
                data_start = seq_num * self.data_size
                data_end = data_start + self.data_size
                data = self.data[data_start:data_end]
                dg = Segment().get(seq_num, data)
                self.server_sock.sendto(dg, self.server_address)
                counters.append(time.time())
                seq_num += 1
                window_free -= 1
            try:
                last_ack_recv = -1
                while 1:
                    ack = self.server_sock.recvfrom(64)  # check buffersize
                    ack_dg = Segment(ack, self.MSS)
                    last_ack_recv = ack_dg.seq_num % self.window_size
                    for i in range(last_ack_recv + 1):
                        counters = -1
            except:
                all_ack = True
                for i in range(self.window_size):
                    if counters[i] != -1:
                        if time.time() - counters[i] > self.TIMEOUT:
                            window_free = window_size - last_ack_recv
                            seq_num = seq_num - window_free
                            all_ack = False
                            print("Timeout, sequence number = ", seq_num - window_size + i)
                            break
                if all_ack:
                    window_free = self.window_size


    def selective_repeat(self):
        return


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
    client = SftpClient(server_host=server_host, server_port=server_port, file_name=file_name,
                        window_size=window_size, MSS=MSS)
    client.start()

