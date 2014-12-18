import zmq

def main():
    context = zmq.Context()
    routers = ['tcp://127.0.0.1:5560', 'tcp://127.0.0.1:5561']

    primary_router = context.socket(zmq.SUB)
    primary_router.setsockopt(zmq.SUBSCRIBE, '')
    primary_router.connect(routers[0])

    backup_router = context.socket(zmq.SUB)
    backup_router.setsockopt(zmq.SUBSCRIBE, '')
    backup_router.connect(routers[1])

    poller = zmq.Poller()
    poller.register(primary_router, zmq.POLLIN)
    poller.register(backup_router, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())
        if socks.get(primary_router) == zmq.POLLIN or socks.get(backup_router) == zmq.POLLIN:
            if primary_router in socks:
                print "Message from primary router"
                message = primary_router.recv(zmq.NOBLOCK)
            elif backup_router in socks:
                print "Message from backup router"
                message = backup_router.recv(zmq.NOBLOCK)
            if message != "HB":
                # Wasn't just a heartbeat
                # Do some meaningful work (who would just square a number?)
                num = int(message.split(' ')[1])
                print "Square of %s = %d" % (message,num*num)

if __name__ == "__main__":
    main()

