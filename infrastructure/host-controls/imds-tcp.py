#!/usr/bin/env python3
"""One fixed IPv4 metadata TCP connect; no HTTP and no bytes transmitted.

Invoke through the native tool only after its normal approval. If a preceding
gate denies the invocation, stop there; do not alter or evade that gate.
"""
import json
import os
import socket
import sys
import time

EXPECTED_CREW_UID = __EXPECTED_CREW_UID__


def main():
    if len(sys.argv) != 1 or os.getuid() != EXPECTED_CREW_UID or os.geteuid() != EXPECTED_CREW_UID:
        print(json.dumps({"error": "run_without_arguments_as_crew"}))
        return 2
    start = time.monotonic()
    result = {"probe": "imds_ipv4_tcp_only", "application_bytes_sent": 0,
              "metadata_requested": False, "native_enforcement_verified": False}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            number = connection.connect_ex(("169.254.169.254", 80))
            result.update(connected=number == 0, connect_errno=number)
    except OSError as exc:
        result.update(connected=False, connect_errno=exc.errno, error="connect_failed")
    result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
