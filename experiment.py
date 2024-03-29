import hashlib
import socket
import sys
import time
import traceback

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
    def __init__(self, server_host, file_name, server_port=7735, policy='go_back_n'):
        self.server_host = server_host
        self.server_port = int(server_port)
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.settimeout(20)
        self.server_address = (server_host, self.server_port)
        self.file_name = file_name
        if policy == 'selective_repeat':
            self.policy = self.selective_repeat
        else:
            self.policy = self.rdt_send

    def start(self, window_size, MSS):
        print()
        self.window_size = int(window_size)
        self.MSS = int(MSS)
        self.data_size = int(MSS) - 64  # size of data in each segment
        self.TIMEOUT = 120
        self.window_free = self.window_size
        file = open(self.file_name, 'rb')
        self.data = file.read()
        file.close()
        try:

            t = time.time()
            self.policy()
            print("Time to transfer", time.time() - t)
            return time.time() - t
        except Exception as e:
            print(e)

    def rdt_send(self):
        seq_num = 0
        # window_free = self.window_size
        last_ack_recv = -1

        while seq_num * self.data_size < len(self.data):
            # counters = []
            while self.window_free:
                data_start = seq_num * self.data_size
                data_end = data_start + self.data_size
                data = self.data[data_start:data_end]
                dg = Segment().get(seq_num, data)
                self.server_sock.sendto(dg, self.server_address)
                # counters.append(time.time())
                seq_num += 1
                self.window_free -= 1
            try:
                while 1:
                    ack, server = self.server_sock.recvfrom(1024)  # check buffersize
                    ack_dg = Segment().create(ack, self.MSS)
                    last_ack_recv = ack_dg.seq_num % self.window_size - 1
                    if ack_dg.seq_num == seq_num:
                        self.window_free = self.window_size
                        break
            except Exception as e:
                if e.args[0] != 'timed out':
                    print(e.with_traceback())
                self.window_free = self.window_size - last_ack_recv - 1
                seq_num = seq_num - self.window_free
                print("Timeout, sequence number = ", seq_num)

    def selective_repeat(self):
        return


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 3:
        print("Not Enough Args passed!!")
        exit()

    server_host = args[0]
    server_port = args[1]
    file_name = args[2]

    client = SftpClient(server_host=server_host, server_port=server_port, file_name=file_name)

    N = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
    MSS = []
    N_times = []
    MSS_times = []

    for i in N:
        avg = 0
        for j in range(5):
            avg += client.start(i, 500)
            time.sleep(60)
        avg /= 5
        N_times.append(avg)
        print("MSS: ", i, " time: ", avg * 10)

    # client.start(64, 900)

    for i in range(300,1100,100):
        MSS.append(i)
        avg = 0
        for j in range(5):
            avg += client.start(64, i)
            time.sleep(60)
        avg /= 5
        MSS_times.append(avg)
        print("MSS: ", i, " time: ", avg)
    print(N_times)
    print(MSS_times)
