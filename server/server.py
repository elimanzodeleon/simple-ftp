import socket
import subprocess
import sys

HEADER = 10
MAX_SIZE = 65536

# ________________
# HELPER FUNCTIONS
# ________________

# Send all data, either control or data connection
# from the specified socket
def send_msg(sock, data):
    bytes_sent = 0

	# Keep sending till all is sent
    while len(data) > bytes_sent:
        bytes_sent += sock.send(data[bytes_sent:])


def create_header(msg):
    # append white space to len of the data that is being sent
    # used to notify server how many bytes to read in from buffer
    return f'{len(msg):<{HEADER}}'

# __________
# MAIN LOGIC
# __________

# get server port from CLI
# exit if incorrect number of arguments
if len(sys.argv) != 2:
    sys.exit('USAGE python: server.py <PORT NUMBER>')

# port on which to listen
listen_port = int(sys.argv[1])

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('', listen_port)) # bind socket to port 9999

server_socket.listen(1) # wait for a connection

while True:
    print('Server is waiting for connections...')

    # socket of client and its address(ip, port)
    client_socket, client_addr = server_socket.accept()
    print(f'connection with address {client_addr} has been established')

    # send a welcome message to the client socket
    w = 'welcome to the server'
    w_len = create_header(w)
    send_msg(client_socket, w_len.encode()+w.encode())

    while True:
        # receive len of message
        cmd_len = int(client_socket.recv(HEADER).decode().strip())

        # receive the actual message and parse into a list
        cmd = client_socket.recv(cmd_len).decode().split()
        # action is first item in msg after list conversion
        action = cmd[0]

        if action == 'quit':
            print('client has disconnected')
            break

        elif action == 'get':
            # name of file to be sent to the client
            file_name = cmd[1]
            # client data connection port
            client_data_port = int(cmd[-1])

            # server data socket
            server_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect server data socket to client
            server_data_socket.connect((client_addr[0], client_data_port))

            try:
                with open(file_name, 'rb') as f:
                    file_content = f.read()

                file_status = '0' # 1: file found
                status_len = create_header(file_status)
                send_msg(client_socket, status_len.encode()+file_status.encode())

                # byte size of file
                file_size = len(file_content)
                # keeps track of number of bytes sent
                bytes_sent = 0

                while bytes_sent < file_size:
                    if bytes_sent + MAX_SIZE < file_size:
                        file_chunk = file_content[bytes_sent:bytes_sent+MAX_SIZE]
                    else:
                        file_chunk = file_content[bytes_sent:]

                    # send file chink to client
                    file_chunk_header = create_header(file_chunk)
                    send_msg(server_data_socket,
                             file_chunk_header.encode()+file_chunk)

                    # increase the number of bytes sent
                    bytes_sent += MAX_SIZE

                print(f'sent {file_name} to client')

            except FileNotFoundError:
                print(f'{file_name} does not exist on this server')
                file_status = '1 file not found' # 1: file not found
                status_len = create_header(file_status)
                send_msg(client_socket, status_len.encode()+file_status.encode())

            # close server data socket since file has been transferred
            server_data_socket.close()

        elif action == 'put':
            # name of file to be sent to the client
            file_name = cmd[1]
            # client data connection port
            client_data_port = int(cmd[-1])

            # server data socket
            server_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect server data socket to client
            server_data_socket.connect((client_addr[0], client_data_port))

            bytes_received = 0
            while True:
                # receive file chunk size
                file_chunk_size = int(server_data_socket.recv(HEADER).decode().strip())
                # receive file chunk
                file_chunk = server_data_socket.recv(file_chunk_size)
                # print(f'chunk received: {file_chunk.decode()} with size {file_chunk_size}')

                # write file chunk to file
                # 'ab': if file dne, new file created
                # else the chunk is appended to the file
                with open(file_name, 'ab') as new_file:
                    new_file.write(file_chunk)

                if file_chunk_size < MAX_SIZE:
                    # last chunk received, we can exit
                    break

            print(f'received {file_name} from client')

            # close esrver data socket once file has been uploaded from client
            server_data_socket.close()

        elif action == 'ls':
            # client data connection port
            client_data_port = int(cmd[-1])

            # server data socket
            server_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect server data socket to client
            server_data_socket.connect((client_addr[0], client_data_port))

            # save output of 'ls' within server
            ls_output = subprocess.check_output(['ls'])
            len_ls_output = len(ls_output)

            # send ls ouput to client
            bytes_sent = 0

            while bytes_sent < len_ls_output:
                if bytes_sent + MAX_SIZE < len_ls_output:
                    ls_chunk = ls_output[bytes_sent:bytes_sent+MAX_SIZE]
                else:
                    ls_chunk = ls_output[bytes_sent:]

                # header indiciating size of chunk
                chunk_header = create_header(ls_output)
                # send chunk
                send_msg(server_data_socket, chunk_header.encode()+ls_chunk)

                bytes_sent += MAX_SIZE

            print(f'sent files available on server to client')

    # close connection to client socket
    client_socket.close()
