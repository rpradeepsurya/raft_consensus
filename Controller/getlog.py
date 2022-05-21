import json
import socket
import traceback
import time
import sys
import threading

def listen(skt):
    while True:
        try:
            msg, addr = skt.recvfrom(1024)
            # Decoding the Message received from Node 
            if addr:
                decoded_msg = json.loads(msg.decode('utf-8'))
                print()
                print("----- Response ------")
                print(decoded_msg)
                print()
                break
        except:
            print(f"ERROR while fetching from socket : {traceback.print_exc()}")

if __name__ == "__main__":

    # Wait following seconds below sending the controller request
    #time.sleep(0.5)

    # Read Message Template
    msg = json.load(open("Message.json"))

    # Initialize
    sender = "Controller"
    target = sys.argv[1]
    port = 5555

    # Request
    msg['sender_name'] = sender
    msg['request'] = "GETLOG"
    print(f"Request Created : {msg}")
    #print(f"Get leader info from all nodes")
    # Socket Creation and Binding
    skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    skt.bind((sender, port))
    #Starting thread 1
    threading.Thread(target=listen, args=[skt]).start()
    # Send Message
    try:
        # Encoding and sending the message
        skt.sendto(json.dumps(msg).encode('utf-8'), (target, port))

    except:
        #  socket.gaierror: [Errno -3] would be thrown if target IP container does not exist or exits, write your listener
        print(f"ERROR WHILE SENDING REQUEST ACROSS : {traceback.format_exc()}")

