import socket
import threading
import time
import numpy as np
import json
import queue

HEADERSIZE = 10
game_board = np.array([[0] * 70] * 70)  # Game Board
game_over = False

task_list = [] # Help to synchronize the player threads
task_queue = queue.Queue()  # Help to synchronize the player threads

all_players_moves = [None] * 4


def initilize_wall():
    i = 0
    for k in range(70):
        game_board[i][k] = 1
    i = 69
    for k in range(70):
        game_board[i][k] = 1

    k = 0
    for i in range(70):
        game_board[i][k] = 1
    k = 69
    for i in range(70):
        game_board[i][k] = 1


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


# check and see if a position in a gameboard has already been taken.
def validate_position(position):
    # position[0] is row, position[1] is column
    if game_board[position[0]][position[1]] == 0:
        game_board[position[0]][position[1]] = 1
        return "ok"
    else:
        return "boom"  # "boom" means you exploded


def handle_all_players(game_play_socket, num_of_players, port):
    global all_players_moves
    global HEADERSIZE
    global task_list
    global task_queue

    task_list = [False] * num_of_players.value
    print("game play created with ", num_of_players.value, "players")

    # game_play_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # game_play_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #
    # game_play_socket.bind(("", port))
    # game_play_socket.listen(5)

    all_players_socket = []
    all_players_threads = []
    initilize_wall()

    # accepting players and initialize task_queue
    for i in range(num_of_players.value):
        player_socket, addr = game_play_socket.accept()
        print("a player connected")
        all_players_socket.append(player_socket)
        player_thread = threading.Thread(target=handle_each_player_move, args=(player_socket, i))
        all_players_threads.append(player_thread)

    print("all player socket", len(all_players_socket))
    print("finish accept players")
    # # synchronize start time for all players
    # header = f'{len("start".encode()):<{HEADERSIZE}}'.encode()
    # for player_socket in all_players_socket:
    #     player_socket.send(header + "start".encode())

    # start listening to each player's moves
    for player_thread in all_players_threads:
        player_thread.start()

    while True:
        if (num_of_players.value == 0):
            break
        if task_queue.qsize() == 0:
            # message = str(all_players_moves).encode()
            message = str(all_players_moves).encode()
            header = f'{len(message):<{HEADERSIZE}}'.encode()
            # send player move to all players
            for i in range(num_of_players.value):
                try:
                    all_players_socket[i].send(header + message)
                except (ConnectionResetError, ConnectionAbortedError):
                    print("Disconnected from input_server")
                    del all_players_socket[i]
                    del task_list[i]
                    num_of_players.value -=1
                    break
                task_queue.put(None)
                task_list[i] = True

        # time.sleep(0.01)  # give CPU to other thread

        # for player_thread in all_players_threads:
        #     player_thread.join()

        # TODO: remove room after game is over


def handle_each_player_move(player_socket, thread_id):
    global task_queue
    global task_list
    global all_players_moves
    global HEADERSIZE
    player_move = {}

    while True:
        if task_queue.qsize() > 0:
            if task_list[thread_id]:
                task_list[thread_id] = False
                # # TODO: Do your stuffs here

                print("waiting for player to send move")
                print(player_socket)
                # print("thread id", thread_id)
                msg = receive_message(player_socket)
                print(msg)

                # print("waiting for player to send move")

                try:
                    json_msg = json.loads(msg.decode("utf-8"))
                    speed = int(json_msg["speed"])
                    direction = json_msg["direction"]
                    player_position = json_msg["position"].split("+")  # convert player's move from string to tuple.

                    # player_id = json_move['playerID']
                    #
                    # Validate player's move
                    position_status = []
                    for position in player_position:
                        move = json.loads(position)
                        print(move)
                        position_status.append(validate_position(move))

                    player_move["position"] = position_status
                    player_move["speed"] = speed
                    player_move["direction"] = direction

                    all_players_moves[thread_id] = player_move

                except AttributeError:
                    pass #player disconnected


                # all_players_moves_json = json.loads("{}")
                task_queue.get() # change the order of task_queue.get() and task_list[thread_id] = False and it worked like a champ

            time.sleep(0.01)  # give CPU time to other threads


# check and see if two or more players move at the same position.
def appear_at_least_twice(all_player_move_positions, player_position):
    count = 0
    for position in all_player_move_positions:
        if player_position == position:
            count += 1
            if count == 2:
                return True
    return False
