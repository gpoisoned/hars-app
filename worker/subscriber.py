import threading
import zmq
from Queue import Queue

def main():
    context = zmq.Context()
    message_queue = Queue()

    routers = ['tcp://127.0.0.1:5560', 'tcp://127.0.0.1:5561']

    router_number = 0 # Always try to connect to Primary Router first

    router_connection = context.socket(zmq.SUB)
    router_connection.setsockopt(zmq.SUBSCRIBE, '')
    print "Connecting to router: %s" % routers[router_number]
    router_connection.connect(routers[router_number])

    poller = zmq.Poller()
    poller.register(router_connection, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())
        if socks.get(router_connection) == zmq.POLLIN:
            message = router_connection.recv(zmq.NOBLOCK)
            if message != "HB":
                # Wasn't just a heartbeat
                # Do some meaningful work (who would just square a number?)
                num = int(message.split(' ')[1])
                print "Square of %s = %d" % (message,num*num)
        else:
            # Router is probably dead
            print "No Heartbeat.Failing over to backup router..."
            poller.unregister(router_connection)
            router_connection.close()
            # Change router and recreate sockets
            router_number = (router_number + 1) % 2
            router_connection = context.socket(zmq.SUB)
            poller.register(router_connection, zmq.POLLIN)
            # reconnect and resend request
            router_connection.connect(routers[router_number])

if __name__ == "__main__":
    main()
