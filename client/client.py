import socket
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

# exit if incorrect number of arguments
if len(sys.argv) != 3:
    sys.exit('USAGE python: client.py <SERVER MACHINE> <SERVER PORT>')

# server name, ip, port
server_name = sys.argv[1]
server_ip = socket.gethostbyname(server_name)
server_port = int(sys.argv[2])
server_addr = (server_ip, server_port)

# client socket used for connection to server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# connect client socket to server socket at 127.0.0.1:9999
client_socket.connect(server_addr)

# TEST
m_len = int(client_socket.recv(HEADER).strip().decode()) # welcome message len
msg = client_socket.recv(m_len).decode() # receive actual message len

# msg = recv_all(client_socket)
print(msg)

while True:
    cmd = input('FTP > ').lower()
    action = cmd.split(' ')[0]

    if action == 'quit':
        # header if user entered quit
        cmd_len = create_header(cmd)
        # send user cmd to server (header(len of cmd)+cmd)
        send_msg(client_socket, cmd_len.encode()+cmd.encode())
        print('successfully disconnected from server')
        break

    elif action in ['get', 'put', 'ls']:
        # create eph port
        client_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to port 0
        client_data_socket.bind(('', 0))
        # Retrieve the ephemeral port number
        client_data_port = client_data_socket.getsockname()[1]
        # Start listening on the socket (client side)
        client_data_socket.listen(1)

        # header if user entered get <FILE>, this header includes eph port
        cmd = f'{cmd} {str(client_data_port)}'
        cmd_len = create_header(cmd)
        send_msg(client_socket, cmd_len.encode()+cmd.encode())

        # accept connection from server
        server_data_socket, server_data_addr = client_data_socket.accept()

        if action == 'get':
            # name under which file sent from server will be saved
            file_name = cmd.split(' ')[1]

            # check msg from server on file status
            status_len = int(client_socket.recv(HEADER).decode().strip())
            # reveive the next 'status_len' bytes from the buffer
            file_status = client_socket.recv(status_len).decode()

            # notify user if file dne on server
            if file_status[0] == '1':
                print(file_status[2:])
                continue

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

            # close socket
            client_data_socket.close()


        elif action == 'put':
            file_name = cmd.split(' ')[1]

            try:
                with open(file_name, 'rb') as f:
                    file_content = f.read()

                # size of file to keep track of how much needs to be sent
                file_size = len(file_content)
                # num of bytes keeps track of bytes sent
                bytes_sent = 0

                # send file in chunks
                while bytes_sent < file_size:
                    if bytes_sent + MAX_SIZE < file_size:
                        file_chunk = file_content[bytes_sent:bytes_sent+MAX_SIZE]
                    else:
                        file_chunk = file_content[bytes_sent:]

                    # send file chunk to server
                    file_chunk_header = create_header(file_chunk)
                    send_msg(server_data_socket,
                             file_chunk_header.encode()+file_chunk)

                    bytes_sent += MAX_SIZE

            except FileNotFoundError:
                print('File does not exist')

            # close socket
            client_data_socket.close()

        elif action == 'ls':
            bytes_received = 0
            while True:
                # size of chunk sent by server
                chunk_size = int(server_data_socket.recv(HEADER).decode().strip())
                # receive chunk from server and decode since printing to console
                ls_chunk = server_data_socket.recv(chunk_size).decode()
                # print server ls output in client
                print(ls_chunk)

                if chunk_size < MAX_SIZE:
                    # last chunk so we can exit loop
                    break

            # close server data socket
            server_data_socket.close()

    else:
        print('USAGE:\
               \n\tFTP > get <FILENAME> # download <FILENAME> from server\
               \n\tFTP > put <FILENAME> # upload <FILENAME> to server\
               \n\tFTP > ls # list files on server\
               \n\tFTP > quit # disconnect from server and exit')

# close persistent control connection
client_socket.close()
