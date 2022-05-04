import socket
import multiprocessing
import sys
import threading
import queue
import json

import time
import game_play
import os

all_players_socket = [None] * 4
all_players_names = [None] * 4
this_game_room_id = ""
HEADERSIZE = 10
game_started = False

game_room_socket = None

def handle_game_lobby(game_room_id, game_socket, all_game_rooms, num_of_players):
    global all_players_socket
    global all_players_names
    global game_room_socket

    game_room_socket = game_socket
    # if after 3 seconds, no one join the game lobby, then it will destroy itself
    game_room_socket.settimeout(3)
    try:
        # accept the host first
        client_socket, client_address = game_room_socket.accept()
        print("a player connected")
        num_of_players.value +=1
        game_room_socket.settimeout(None)
    except socket.timeout:
        del all_game_rooms[game_room_id]
        sys.exit()

    # receive player's name
    player_name = receive_message(client_socket).decode()

    all_players_socket[0] = client_socket
    all_players_names[0] = player_name
    host = "player1"

    # send room information to player
    send_room_information(client_socket, 0, host, all_game_rooms, num_of_players)

    # accept non-host players
    while not game_started:
        player_added = False
        player_order = -9999
        try:
            client_socket, client_address = game_room_socket.accept()
        except OSError:
            print("phantom socket killed")
            os._exit(1)
        print("a player connected")

        # receive player's name
        for i in range(4):
            if all_players_socket[i] == None:
                all_players_socket[i] = client_socket
                num_of_players.value +=1
                print("num of player ", num_of_players.value)
                player_name = receive_message(client_socket).decode()
                all_players_names[i] = player_name
                player_order = i
                player_added = True
                break

        # send message to player's lobby
        try:
            if not player_added:
                print("Room is full")
            else:
                send_room_information(client_socket, player_order, host, all_game_rooms, num_of_players)
        except (ConnectionResetError, ConnectionAbortedError):
            print("Disconnected from input_server")
            num_of_players.value -=1
            break

        # send all_players_names to all players. At this stage, if the game room has no-one, it will self-destruct
        send_update_information(all_game_rooms)



def send_room_information(client_socket, playerOrder, host, all_game_rooms, num_of_players):
    print("player" +str(playerOrder+1) + "connected")
    # send game room information to the player
    message = {}
    message["myPlayer"] = "player" + str(playerOrder+1)
    message["host"] = host
    message["allPlayersNames"] = all_players_names
    message = json.dumps(message).encode()
    header = f'{len(message):<{HEADERSIZE}}'.encode()
    client_socket.send(header + message)
    threading.Thread(target=listen_for_player_button_clicked, args=(client_socket, playerOrder, all_game_rooms, num_of_players)).start()

def send_update_information(all_game_rooms):
    global this_game_room_id
    # send all_players_names to all players
    num_of_active_player = 0
    for i in range(4):
        try:
            player = all_players_socket[i]
            if player is not None:
                num_of_active_player += 1
                message = json.dumps(all_players_names).encode()
                header = f'{len(message):<{HEADERSIZE}}'.encode()
                player.send(header + message)
        except (ConnectionResetError, ConnectionAbortedError):
            print("Disconnected from input_server")
            all_players_names[i] = None
            all_players_socket[i] = None
            num_of_players.value -= 1
            break

    print("all player sockets ", all_players_socket)
    # destroy the game room if no player is connecting
    if num_of_active_player == 0:
        os._exit(1)


def listen_for_player_button_clicked(client_socket, player_order, all_game_rooms, num_of_players):
    global all_players_socket
    global game_started
    global game_room_socket
    try:
        message = receive_message(client_socket).decode()
        if message == "leave":
            all_players_socket[player_order].close() # might not need
            all_players_socket[player_order] = None
            all_players_names[player_order] = None
            num_of_players.value -= 1
            print("a player left the game")
            send_update_information(all_game_rooms)
        elif message == "host_start":
            # the host started the game
            #game_room_socket.close()
            print(message)
            message = "host_start".encode()
            header = f'{len(message):<{HEADERSIZE}}'.encode()
            for i in range(4):
                if all_players_socket[i] != None:
                    try:
                        all_players_socket[i].send(header + message)
                        all_players_socket[i] = None
                        all_players_names[i] = None
                    except (ConnectionResetError, ConnectionAbortedError):
                        all_players_socket[i] = None
                        all_players_names[i] = None
                        send_update_information(all_game_rooms)
            #os._exit(1)
            #os._exit(1) #kill the lobby
        else: # non-host send "start" to exit lobby
            game_room_socket.close() # this will raise OSError for the remaining socket.accept(), making it a phantom.
            os._exit(1)
    except (ConnectionResetError, ConnectionAbortedError):
        print("Disconnected from input_server")
        # all_players_socket[player_order].close()  # might not need
        all_players_socket[player_order] = None
        all_players_names[player_order] = None
        num_of_players.value -= 1
        send_update_information(all_game_rooms)


def start_game_room(game_room_id, port, all_game_rooms):
    global this_game_room_id
    num_of_players = multiprocessing.Value('i', 0)
    this_game_room_id = game_room_id


    game_room_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    game_room_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


    game_room_socket.bind(("", port))
    game_room_socket.listen(5)

    # Handle the lobby
    handle_game_lobby_process = multiprocessing.Process(target=handle_game_lobby, args = (game_room_id, game_room_socket,all_game_rooms, num_of_players))
    handle_game_lobby_process.start()
    handle_game_lobby_process.join()
    # socket_killer = socket.socket()
    # socket_killer.connect(("127.0.0.1", port))

    if num_of_players.value == 0:
        try:
            del all_game_rooms[game_room_id]
        except KeyError:
            pass
        print("detroy game lobby")
    else:
        game_play.handle_all_players(game_room_socket, num_of_players, port)




    # Handle the game play
    # handle_game_play_process = multiprocessing.Process(target= game_play.handle_all_players, args=(game_room_socket, num_of_players, port))
    # handle_game_play_process.start()
    # print("started handle game play")
    # handle_game_play_process.join()

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


# if __name__ == "__main__":
#     main()
