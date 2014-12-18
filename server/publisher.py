from flask import Flask, jsonify
import threading
import zmq
import time
import logging
from Queue import Queue

# Clear the Log file if it exists
with open("server.log", "w"):
    pass

logging.basicConfig(filename='server.log',level=logging.DEBUG,\
        format='%(levelname)s:%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

app = Flask(__name__)
context = zmq.Context()

servers = ['tcp://127.0.0.1:5558', 'tcp://127.0.0.1:5559']
servers_heartbeats = ['tcp://127.0.0.1:6668', 'tcp://127.0.0.1:6669']
server_nbr = 0
message_queue = Queue()

primary_router_msg = context.socket(zmq.PUB)
primary_router_msg.connect(servers[0])

backup_router_msg = context.socket(zmq.PUB)
backup_router_msg.connect(servers[1])

@app.route("/square/<int:num>")
def square(num):
    message_queue.put(num)
    return jsonify(status="Work will be sent to worker!")

@app.route("/")
def root():
    return jsonify(status="Web server is running!")

@app.route("/health")
def health():
    return jsonify(heath="It's all good :)")

def message_sender():
    global servers
    global server_nbr
    global context
    global send_message
    while True:
        message =  message_queue.get()
        print message
        if server_nbr == 0:
            primary_router_msg.send("%s %s" %("DATA", message))
        elif server_nbr == 1:
            backup_router_msg.send("%s %s" %("DATA", message))
        message_queue.task_done()

# Background thread to do heartbeat with router
def heartbeat_listener():
    # We want to modify the global states server_nbr
    # and use global zeromq context
    global servers_heartbeats
    global server_nbr
    global context

    HEARTBEAT_TIMEOUT = 1000 * 5 # Timeout in seconds
    DELAY = 3000
    router_heartbeat = context.socket(zmq.REQ)
    router_heartbeat.connect(servers_heartbeats[server_nbr])

    poller = zmq.Poller()
    poller.register(router_heartbeat, zmq.POLLIN)
    heartbeat = "HB"
    while True:
        try:
            router_heartbeat.send(heartbeat,zmq.NOBLOCK)
            expect_reply = True
        except:
            except_reply = False
            pass
        while expect_reply:
            socks = dict(poller.poll(HEARTBEAT_TIMEOUT))
            if router_heartbeat in socks:
                reply = router_heartbeat.recv(zmq.NOBLOCK)
                expect_reply = False
            else:
                logging.warning("Router is probably dead. Connecting to backup router")
                time.sleep(DELAY/1000)
                # Unregister old socket and delete it
                poller.unregister(router_heartbeat)
                router_heartbeat.close()
                # Change server and recreate sockets
                server_nbr = (server_nbr + 1) % 2
                router_heartbeat = context.socket(zmq.REQ)
                poller.register(router_heartbeat, zmq.POLLIN)
                # reconnect and resend request
                router_heartbeat.connect(servers_heartbeats[server_nbr])
                router_heartbeat.send(heartbeat,zmq.NOBLOCK)


if __name__ == "__main__":
    app.debug = True
    logging.info("Starting a heartbeat daemon process...")
    listner = threading.Thread(name="Heartbeat_listener", target = heartbeat_listener).start()
    sender = threading.Thread(name="Message sender", target = message_sender).start()
    logging.info("**** Daemon started. Now running app server ****")
    app.run(threaded=True)
    logging.error("App server crashed.")
    context.term()
