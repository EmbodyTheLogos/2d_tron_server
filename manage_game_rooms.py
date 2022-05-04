from multiprocessing import Process, Manager
import string
import random
import game_room_old
import time
import sys

available_ports = {} # True means available, False means the port already in use.

def initialize_ports():
    global available_ports
    for i in range(5400, 5800):
        available_ports[i] = True

# https://www.geeksforgeeks.org/python-get-key-from-value-in-dictionary/
def get_port():
    global available_ports
    for port, ret in available_ports.items():
        if ret == True:
            available_ports[port] = False
            return port
    return None


# Reference: https://blog.actorsfit.com/a?ID=00500-40efd917-174c-4268-818f-778c20b9821b
# Reference: https://stackoverflow.com/questions/2511222/efficiently-generate-a-16-character-alphanumeric-string
def generate_room_id(all_rooms):
    seed = string.ascii_uppercase + string.ascii_lowercase + string.digits
    room_id = ""
    while True:
        for i in range(8):
            random_index = random.randrange(0, len(seed) - 1)
            room_id += seed[random_index]
        if room_id not in all_rooms:
            return room_id

def main():
    initialize_ports()
    room_processes = []
    all_rooms = Manager().dict()

    game_host = "this is the person who created the game"
    for i in range(30):
        game_port = get_port()
        print(game_port)
        room_id = generate_room_id(all_rooms)
        p = Process(target=game_room_old.new_room, args=(room_id, game_port, all_rooms, game_host))
        p.start()

        room_processes.append(p)

    time.sleep(4)
    print(all_rooms)
    for p in room_processes:
        p.join()

if __name__ == '__main__':
    main()
