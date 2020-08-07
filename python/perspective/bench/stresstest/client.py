################################################################################
#
# Copyright (c) 2019, the Perspective Authors.
#
# This file is part of the Perspective library, distributed under the terms of
# the Apache License 2.0.  The full license can be found in the LICENSE file.
#
import random
import logging
import json
from tornado import gen, ioloop, locks, websocket


class PerspectiveWebSocketClient(object):

    def __init__(self, url, timeout=None):
        """Create a PerspectiveWebSocketClient that mimics a Perspective Viewer
        through the wire API.

        Examples:
            >>> @gen.coroutine
            >>> def run_client(URL):
            >>>     client = PerspectiveWebSocketClient(URL)
            >>>     # Connect to the server and send the initialization message
            >>>     yield client.connect()
            >>>     # Register an on_update callback to handle new ticks
            >>>     yield client.register_on_update()
            >>>     # Run a set of messages
            >>>     yield client.start()
        """
        self.url = url
        self.client = None

        # The number of seconds this client should run before timing out. The
        # default timeout of None means this client will run forever.
        self.timeout = timeout

        # Each message must have a unique integer ID
        self.message_id = -1

        # The total number of messages that should be sent to the server on
        # every call to `self.run()`
        self.total_messages = 30
        self.cmds = ["table_method", "view_method"]

        # A list of views created by this client
        # TODO create view on init
        self.views = ["view"]

        # A list of messages that can be decomposed into *args for
        # self._make_message
        self.table_methods = ["schema", "size"]
        self.table_methods_mutate = ["update"]
        self.view_methods = ["schema", "computed_schema", "column_paths", "sides", "to_json", "to_columns"]

        # `on_update` callbacks managed by this client
        self.callbacks = {}

    @gen.coroutine
    def connect(self):
        """Create and maintain a websocket client to Perspective, initializing
        the connection with the `init` message."""
        self.client = yield websocket.websocket_connect(self.url)
        yield self.write_message({"id": self.message_id, "cmd": "init"})

    @gen.coroutine
    def write_message(self, message):
        """Wrap websocket.write_message to coerce messages to JSON-serialized
        strings from dicts, and read the next message on the websocket."""
        ioloop.IOLoop.current().add_callback(
            self.client.write_message,
            json.dumps(message)
        )
        self.message_id += 1
        yield self.read_message()

    @gen.coroutine
    def read_message(self):
        """Read messages from the WebSocket server."""
        message = yield self.client.read_message()
        try:
            response = self.parse_response(message)
            response_id = response["id"]
            logging.info("Received id: %s", response_id)

            if response["id"] in self.callbacks:
                # Call the on_update callback
                ioloop.IOLoop.current().add_callback(self.callbacks[response_id], self)
        except AssertionError:
            logging.CRITICAL("Server returned error:", message)

    @gen.coroutine
    def run(self):
        """Send random messages at intervals that simulate the actions of a
        Perspective viewer in the front-end."""
        for i in range(self.total_messages):
            message = None
            cmd = "view_method" if random.random() > 0.5 else "table_method"

            if cmd == "view_method":
                view_name = random.choice(self.views)
                method = random.choice(self.view_methods)
                args = []

                if "to" in method:
                    args.append({
                        "start_row": random.randint(0, 500),
                        "end_row": random.randint(501, 1000)
                    })

                message = self._make_message(
                    cmd=cmd,
                    name=view_name,
                    method=method,
                    args=args)
            else:
                method = random.choice(self.table_methods)
                message = self._make_message(
                    cmd=cmd,
                    name="table",
                    method=method)

            logging.info("Sending %s, id: %s", cmd, message["id"])
            yield self.write_message(message)

            # sort of simulate wait times between user actions
            if random.random() > 0.75:
                wait_time = random.random()
                logging.info("Waiting for %s", wait_time)
                yield gen.sleep(wait_time)

    @gen.coroutine
    def run_forever(self):
        yield self.run()
        while True:
            if random.random() > 0.8:
                # inject more user actions at random
                yield self.run()
            yield self.read_message()

    @gen.coroutine
    def register_on_update(self):
        """Registers an `on_update` callback that mimics the callback of the
        viewer by requesting more metadata from the server whenever it updates,
        thereby calling back into the Tornado IOLoop on the server."""
        @gen.coroutine
        def on_update(self):
            # Send 5 more messages back to the server whenever on_update
            # happens, with no sleep time to simulate the Viewer requesting
            # more information from the server.
            for i in range(5):
                # non-mutating methods only
                method = random.choice(("schema", "num_rows", "column_paths"))
                view_name = random.choice(self.views)

                message = self._make_message(
                    cmd="view_method",
                    name=view_name,
                    method=method)

                logging.info("Sending within on_update %s, id: %s", method, message["id"])
                yield self.write_message(message)

        # Store callbacks as they would be on the viewer - by message ID
        self.callbacks[self.message_id] = on_update

        # send the message that registers on_update
        on_update_message = self._make_message(
            "view_method",
            "view",
            "on_update",
            subscribe=True,
            callback_id="callback_1")

        yield self.write_message(on_update_message)

    def parse_response(self, response):
        """Checks that the server has responded with a valid message, i.e. one
        that does not have "error" set, and return the parsed response."""
        res = json.loads(response)
        assert "error" not in res
        return res

    def _make_message(self, cmd, name, method, **kwargs):
        """Returns a message that will execute the given method on the
        server with the specified `args`."""
        msg = {
            "id": self.message_id,
            "cmd": cmd,
            "name": name,
            "method": method,
            "args": [],
        }

        for key in kwargs:
            msg[key] = kwargs[key]

        return msg

    def _make_view_message(self, message_id, name, config={}):
        """Returns a message that will create a view on the server with the
        given `name` and `config`."""
        message = {
            "id": self.message_id,
            "cmd": "view",
            "table_name": "table",
            "view_name": name,
            "config": config
        }

        return message
