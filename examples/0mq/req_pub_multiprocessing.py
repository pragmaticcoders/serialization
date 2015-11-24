#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import unicode_literals

from serialization import json_ as json
from common import Stack, Stacker

import zmq
from multiprocessing import Process

END_MESSAGE = '!__end__!'


def stacker_sum(port="5556"):
    context = zmq.Context()
    with context.socket(zmq.REP) as socket:
        socket.bind("tcp://*:%s" % port)
        print("Running server on port: %d" % port)
        while True:
            # Wait for next request from client
            message = socket.recv_string()
            if message == END_MESSAGE:
                socket.send_string(END_MESSAGE)
                print("Close server on port: %d" % port)
                break
            stack, stacker = json.unserialize(message)
            stacker.add_stack(stack)
            socket.send_string(json.serialize([stacker.sum(), stacker]))


def stack_client(ports=["5556"]):

    context = zmq.Context()
    print("Connecting to server with ports %s" % ports)
    with context.socket(zmq.REQ) as socket:
        for port in ports:
            socket.connect("tcp://localhost:%s" % port)

        stack = Stack(4)
        for n in range(4):
            stack.push(n * 0.001)
        stacker = Stacker()

        for i in range(50):
            socket.send_string(json.serialize([stack, stacker]))
            stack, stacker = json.unserialize(socket.recv_string())
            print(stack)

        for _ in ports:
            socket.send_string(END_MESSAGE)
            socket.recv()


if __name__ == "__main__":
    # Now we can run a few stacker_sum servers
    server_ports = range(5550, 5558, 2)
    for server_port in server_ports:
        Process(target=stacker_sum, args=(server_port,)).start()

    # Now we can connect a stack_client to all these servers
    Process(target=stack_client, args=(server_ports,)).start()
