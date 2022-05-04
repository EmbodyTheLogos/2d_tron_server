import socket
from requests import get

#reference: https://stackoverflow.com/questions/60656088/how-to-get-wireless-lan-adapter-wi-fi-ip-address-in-python?fbclid=IwAR3DJ7al54DRtbgFLwvam9CzAOOeiqyVjf1dIjpaZmgttnDWJdrU55AgS5g
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# reference: https://www.codegrepper.com/code-examples/python/get+public+ip+address+python
def get_public_ip():
    ip = get('https://api.ipify.org').text
    return ip

if __name__ == "__main__":
    print("Your LAN IP is:", get_local_ip())
    print("Your public IP is:", get_public_ip())
