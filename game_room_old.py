import numpy as np
import threading
import time
import queue
import socket

game_socket = socket.socket()
game_over = False
need_new_host = False # if the host left the game, then this set to True.
socket = "Each room has its own socket"
player_id = [-999] * 4
num_of_players = 1
game_started = False        # If the game is started, then we will no longer accept connection.
task_list = [False] * 4     # Help synchronize the player threads
task_queue = queue.Queue()  # Help synchronize the player threads
moves = [(0,0,0)] * 4       # The moves received from all players
moves_status = None # "Ok" means it is a good move. "Boom" means the player made a losing move.
board = np.array([[0] * 70] * 70) #Game Board

# def accept_connection():
#     global player_id
#     global num_of_players
#     while True:
#         if num_of_players < 4:
#             # accept connection
#             player_socket, address = game_socket.accept()
#             for i in range(4):
#                 if player_id[i] is not None:
#                     threading.Thread(target=player_thread, args=(i, player_socket)).start()
#                     player_id[i] = i
#             num_of_players += 1

# this assign the host of the game. The first player in the player_id will be the host.
def assign_new_host():
    global need_new_host
    if need_new_host:
        pass

def new_room(room_id, game_port, all_rooms, game_host):
    global game_started
    global player_id
    global game_socket

    game_socket.bind(('', game_port))
    print("socket binded to %s" % (game_port))

    # put the socket into listening mode
    game_socket.listen(5)
    print("socket is listening")


    all_rooms[room_id] = socket
    print(room_id)

    # initialize host of the game
    player_id[0] = game_host

    # start accepting player
    # threading.Thread(target=accept_connection).start

    for i in range(4):
        threading.Thread(target=player_thread, args=(i,)).start()

    game_started = True
    # When the game started
    if game_started:
        count = 0
        s = time.time()
        while not game_over:
            if task_queue.qsize() == 0:
                for i in range(4):
                    move = moves[i]
                    for k in range(i+1, 4):
                        if move == moves[k]:
                            #print("conflict")
                            pass
                    task_queue.put(None)

                e = time.time()
                print(e-s)
                s = e
                for i in range(4):
                    task_list[i] = True
            time.sleep(0.01)  # simulate send time of socket

# this receive a move from a particular player associated with player_id
def player_thread(player_id):
    global task_queue
    global task_list
    global moves
    while True:
        if task_list[player_id]:
            task_queue.get()
            moves[player_id] = 0, 0
            task_list[player_id] = False
        time.sleep(0.01) # give CPU time to other threads


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



# See PyCharm help at https://www.jetbrains.com/help/pycharm/
