import socket
import time
import multiprocessing
import threading
import display_ip
import string
import random
import json
import game_room

HEADERSIZE = 10

def initialize_ports(available_ports, start_port, end_port):
    for i in range(start_port, end_port + 1):
        available_ports[i] = True


# https://www.geeksforgeeks.org/python-get-key-from-value-in-dictionary/
def get_available_port(available_ports):
    for port, ret in available_ports.items():
        if ret:
            available_ports[port] = False
            return port
    return None


# Reference: https://blog.actorsfit.com/a?ID=00500-40efd917-174c-4268-818f-778c20b9821b
# Reference: https://stackoverflow.com/questions/2511222/efficiently-generate-a-16-character-alphanumeric-string
def generate_room_id(all_game_rooms):
    seed = string.ascii_uppercase + string.ascii_lowercase + string.digits
    room_id = ""
    while True:
        for i in range(8):
            random_index = random.randrange(0, len(seed) - 1)
            room_id += seed[random_index]
        if room_id not in all_game_rooms:
            return room_id



def main():
    # share resources for processes
    all_game_rooms = multiprocessing.Manager().dict()
    available_ports = multiprocessing.Manager().dict()

    initialize_ports(available_ports, 5100, 5500)

    # 2 main processes, one is for handling create game requests, the other is for handling join game requests
    handle_create_game = multiprocessing.Process(target=process_create_game_request,
                                                 args=(all_game_rooms, available_ports))
    handle_join_game = multiprocessing.Process(target=process_join_game_request, args=(all_game_rooms,))

    handle_create_game.start()
    handle_join_game.start()

    handle_create_game.join()
    handle_join_game.join()


def process_create_game_request(all_game_rooms, available_ports):
    # socket for listening to create game request
    create_game_request_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    create_game_request_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    create_game_request_socket.bind(("", 5000))
    create_game_request_socket.listen(50)
    print("socket for create game request created")

    while True:
        client_socket, client_address = create_game_request_socket.accept()
        print("create game request")

        # create a game
        game_room_id = generate_room_id(all_game_rooms)
        game_room_ip = display_ip.get_local_ip()
        game_room_port = get_available_port(available_ports)

        # create a new game room
        multiprocessing.Process(target=game_room.start_game_room, args=(game_room_id, game_room_port, all_game_rooms)).start()
        # game room address is in the form of json array
        all_game_rooms[game_room_id] = "["+ "\"" +  game_room_id + "\"," +"\"" + game_room_ip + "\"," + str(game_room_port) + "]"

        # send game room address to game host
        message = all_game_rooms[game_room_id].encode()
        header = f'{len(message):<{HEADERSIZE}}'.encode()
        client_socket.send(header + message)
        print(all_game_rooms)


def process_join_game_request(all_game_rooms):
    # socket for listening to join game request
    join_game_request_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    join_game_request_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    join_game_request_socket.bind(("", 5001))
    join_game_request_socket.listen(50)
    while True:
        client_socket, client_address = join_game_request_socket.accept()
        print("join game request")
        print(all_game_rooms)

        # receive message from client
        message = receive_message(client_socket)
        try:
            message = json.loads(message.decode())
        except json.JSONDecodeError:
            pass

        try:
            game_room_id = message["game_room_id"]
        except TypeError:
            print("Invalid message. Probably due to different language symbols")

        # send game room address to non-host players
        if game_room_id in all_game_rooms:
            message = all_game_rooms[game_room_id].encode()
            header = f'{len(message):<{HEADERSIZE}}'.encode()
            client_socket.send(header + message)

        else:
            message = "[\"None\"]".encode() # room does not exist
            header = f'{len(message):<{HEADERSIZE}}'.encode()
            client_socket.send(header + message)

def receive_message(input_server):
    global HEADERSIZE

    full_msg = bytearray()
    new_msg = True
    receive_msg_size = HEADERSIZE
    header = ''

    while True:
        try:
            msg = input_server.recv(receive_msg_size)

            # check if the socket has been shutdown and closed or not
            # if msg == b'' and receive_msg_size > 0:
            #    input_server.send("ping".encode()) # if the other end shutdown and close the socket, this will raise a ConnectionAbortedError exception

            full_msg.extend(msg)
            if new_msg:
                header += msg.decode()
                # make sure to receive full header before convert it to int (sometimes, only part of the header is received)
                if len(header) < HEADERSIZE:
                    # print("header not completely received")
                    receive_msg_size = HEADERSIZE - len(header)
                else:
                    msglen = int(header)
                    # print(header)
                    receive_msg_size = 0  # (*) this solved negative message size error in receive buffer below.
                    new_msg = False

            else:
                # ensure receiving full message
                remaining_len = msglen + HEADERSIZE - len(
                    full_msg)  # (*) this can cause negative message size in receive buffer error since full_msg will always be updated after every loop.
                # We ensure full_message is not updated right after we are done with the header by setting the receive_message_size to 0
                # See (*) above
                receive_msg_size = remaining_len
                # Process fullly received message
                if len(full_msg) - HEADERSIZE == msglen:
                    receive_msg_size = HEADERSIZE
                    decoded_data = full_msg[HEADERSIZE:]
                    return decoded_data
        except (ConnectionResetError, ConnectionAbortedError):
            print("Disconnected from input_server")
            break

if __name__ == "__main__":
    main()
