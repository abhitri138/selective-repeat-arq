import sftp_client
import time
import sys

if __name__ == "__main__":
    args = sys.argv[1:]
    server_host = args[0]
    server_port = args[1]
    file_name = args[2]
    N = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
    MSS = []
    N_times = []
    MSS_times = []

    for i in N:
        avg = 0
        for j in range(4):
            avg += sftp_client.main(server_host, server_port, file_name, i, 500)
            time.sleep(40)
        avg /= 4
        N_times.append(avg)
        print("Window Size: ", i, " time: ", avg * 10)
        
        
#     avg = 0
#     for j in range(4):
#         avg += sftp_client.main(server_host, server_port, file_name, 64, 500)
#         time.sleep(40)
#     avg /= 4
#     N_times.append(avg)
#     print(" time: ", avg * 10)
    # client.start(64, 900)
    

    for i in range(100,1100, 100):
        MSS.append(i)
        avg = 0
        for j in range(3):
            avg += sftp_client.main(server_host, server_port, file_name, 64, i)
            time.sleep(40)
        avg /= 3
        MSS_times.append(avg)
        print("MSS: ", i, " time: ", avg * 10)
    print(N_times)
    print(MSS_times)
