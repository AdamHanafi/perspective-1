################################################################################
#
# Copyright (c) 2019, the Perspective Authors.
#
# This file is part of the Perspective library, distributed under the terms of
# the Apache License 2.0.  The full license can be found in the LICENSE file.
#
from datetime import datetime

# The schema of the results table, defined outside of the application code
# for ease of use and consistency across multiple files.
RESULTS_SCHEMA = {
    "client_id": str,
    "cmd": str,
    "method": str,
    "args": str,
    "send_timestamp": datetime,
    "receive_timestamp": datetime,
    "microseconds_on_wire": float,
    "message_id": int,
    "errored": bool,
    "binary": bool,
    "byte_length": int,
    "server_received": datetime,
    "server_start_process_time": datetime,
    "server_send_time": datetime,
    "client_num_messages": int
}