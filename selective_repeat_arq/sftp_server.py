import queue
import random
import socket
import sys



class Segment:
    def __init__(self, bytes):
        self.seq_num = int(bytes[0:32], 2)
        self.checksum = int(bytes[32:32 + 16], 2)
        self.type = int(bytes[32 + 16:32 + 16 + 16], 2)
        self.data = bytes[32 + 16 + 16:].decode()

    def get_ack(self, seq_num):
        ack = "{0:032b}".format(seq_num)
        ack += "{0:016b}".format(0)
        ack += "1010101010101010"
        return ack.encode()


def calculate_checksum(data):
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


class SftpServer:
    def __init__(self, file_name, loss_prob, port=7735, policy='go_back_n'):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.settimeout(20)
        self.port = int(port)
        self.file_name = file_name
        self.buffer = queue.Queue()
        self.loss_prob = float(loss_prob)
        self.seq_num = 0
        if policy == 'selective_repeat':
            self.policy = self.selective_repeat
        else:
            self.policy = self.go_back_n

    def start(self):
        try:
            server_address = ('localhost', int(self.port))
            print('starting up on %s port %s' % server_address)
            self.server_sock.bind(server_address)
            while 1:
                self.policy()
        finally:
            self.server_sock.close()

    def go_back_n(self):
        try:
            seg, client = self.server_sock.recvfrom(65000)  # TO Do: check the buffer size
            dg = Segment(seg)
            checksum = calculate_checksum(seg[32 + 16 + 16:])
            if checksum == dg.checksum:
                rand_num = random.random()
                if self.seq_num == dg.seq_num and rand_num > self.loss_prob:
                    self.seq_num += 1
                    file = open(file_name, "a")
                    file.write(dg.data)
                    while self.buffer.qsize() > 0:
                        prev_dg = self.buffer.get()
                        if self.seq_num == dg.seq_num:
                            file.write(prev_dg.data)
                            self.seq_num += 1
                        else:
                            break
                    file.close()
                    try:
                        self.server_sock.sendto(Segment(seg).get_ack(self.seq_num), client)
                    except:
                        self.seq_num = 0
                else:
                    if self.seq_num == dg.seq_num:
                        print("Packet loss, sequence number = ", dg.seq_num)
                    else:
                        self.buffer.put(dg)
                        try:
                            self.server_sock.sendto(Segment(seg).get_ack(self.seq_num), client)
                        except:
                            self.seq_num = 0


            else:
                print("Packet loss due to checksum issue, sequence number = ", dg.seq_num)
        except Exception as e:
            # print(e)
            print(e)
            self.seq_num = 0

    def selective_repeat(self):
        return


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 3:
        print("Not Enough Args passed!!")
        exit()

    port = args[0]
    file_name = args[1]
    loss_prob = args[2]
    server = SftpServer(port=port, file_name=file_name, loss_prob=loss_prob)
    server.start()
