import zmq
import argparse
import time
import logging

STATE_PRIMARY = 1
STATE_BACKUP = 2

STATUS_ACTIVE = 3
STATUS_PASSIVE = 4

PEER_ACTIVE = 5
PEER_PASSIVE = 6

CLIENT_HEARTBEAT = 7

HEARTBEAT = 3000

class RouterState(object):
    def __init__(self, state=0, status=0, peer_expiry=0, client_status=0, peer_status=0):
        self.state = state
        self.status = status
        self.peer_expiry = peer_expiry
        self.peer_status = peer_status
        self.client_status = client_status

def updateRouterState(router_state):
    # If client request received and peer is expired, set router to active
    if router_state.client_status == CLIENT_HEARTBEAT and router_state.peer_expiry > 0:
        if int(time.time()*1000) > router_state.peer_expiry:
            router_state.status = STATUS_ACTIVE

    # If peer is active and clients aren't connected to router, change router state to passive
    # This means there's already an active server
    if router_state.client_status != CLIENT_HEARTBEAT and router_state.peer_status == STATUS_ACTIVE:
        router_state.status = STATUS_PASSIVE

def main():
    try:
        # Clear the Log file if it exists
        with open("router.log", "w"):
            pass
        # Setup logging format
        logging.basicConfig(filename='router.log',level=logging.DEBUG,\
                    format='%(levelname)s:%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--primary", action="store_true", default=False)
        group.add_argument("--backup", action="store_true", default=False)
        args = parser.parse_args()

        context = zmq.Context()
        #Socket facing clients
        frontend = context.socket(zmq.SUB)
        frontend.setsockopt(zmq.SUBSCRIBE, "")

        #Socket facing services
        backend = context.socket(zmq.PUB)

        # Client heartbeat (Client => publisher)
        client_heartbeat = context.socket(zmq.REP)

        # Peer Router communication sockets
        statepub = context.socket(zmq.PUB)
        statesub = context.socket(zmq.SUB)

        # Current Router State
        router_state = RouterState()

        # Check if the router is primary or backup
        if args.primary:
            logging.info("Running as Primary Router")
            frontend.bind("tcp://*:5558")
            backend.bind("tcp://*:5560")
            client_heartbeat.bind("tcp://*:6668")

            statepub.bind("tcp://*:7778")
            statesub.setsockopt(zmq.SUBSCRIBE, "")
            statesub.connect("tcp://localhost:7779")

            router_state.state = STATE_PRIMARY

        elif args.backup:
            logging.info("Running as Backup Router")
            frontend.bind("tcp://*:5559")
            client_heartbeat.bind("tcp://*:6669")

            statepub.bind("tcp://*:7779")
            statesub.setsockopt(zmq.SUBSCRIBE, "")
            statesub.connect("tcp://localhost:7778")

            router_state.state = STATE_BACKUP

        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(client_heartbeat, zmq.POLLIN)
        poller.register(statesub, zmq.POLLIN)

        send_state_at = int(time.time() * 1000 + HEARTBEAT)
        print send_state_at
        while True:
            time_left = send_state_at - int(time.time() *1000)
            if time_left <  0:
                time_left = 0

            # print "time left: %f" % time_left
            socks = dict(poller.poll(time_left))
            if socks.get(frontend) == zmq.POLLIN:
                message = frontend.recv()
                print "Message received from frontend: %s" % message
                # Forward message to backend
                print "Forward message to backend: %s" % message
                backend.send(message, zmq.NOBLOCK)
            elif socks.get(client_heartbeat) == zmq.POLLIN:
                message = client_heartbeat.recv(zmq.NOBLOCK)
                client_heartbeat.send("HB", zmq.NOBLOCK)
                # print "Hearbeat to Client"
                # Got client heartbeat
                router_state.client_status = CLIENT_HEARTBEAT
                updateRouterState(router_state)

            elif socks.get(statesub) == zmq.POLLIN:
                # Peer sent a heartbeat
                message = statesub.recv(zmq.NOBLOCK)
                print "Heard from Peer %s" % message
                # Update peer state
                router_state.peer_status = int(message)
                router_state.peer_expiry = int(time.time() * 1000) + (2 * HEARTBEAT)
                # Update router state
                updateRouterState(router_state)
                print "Peer expires at %f" % router_state.peer_expiry
            if int(time.time()*1000) >= send_state_at:
                #send state to peer
                statepub.send("%d" % router_state.status)
                send_state_at = int(time.time() * 1000) + HEARTBEAT

        # zmq.device(zmq.FORWARDER, frontend, backend)
    except Exception, e:
        print e
        print "bringing down zmq device"
    finally:
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    main()
