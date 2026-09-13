#!/usr/bin/env python3
"""One anonymous, body-discarding GET to the configured loopback Gateway.

This deliberately uses no browser session, proxy, cookie or authorization
header. A status alone is an observation, not an authentication verdict.
"""
import http.client
import json
import os
import sys
import time

EXPECTED_CREW_UID = __EXPECTED_CREW_UID__
GATEWAY_PORT = __GATEWAY_PORT__


def main():
    if len(sys.argv) != 1 or os.getuid() != EXPECTED_CREW_UID or os.geteuid() != EXPECTED_CREW_UID:
        print(json.dumps({"error": "run_without_arguments_as_crew"}))
        return 2
    start = time.monotonic()
    connection = http.client.HTTPConnection("127.0.0.1", GATEWAY_PORT, timeout=3)
    result = {"probe": "anonymous_gateway_posture", "response_body_read": False,
              "authorization_sent": False, "cookies_sent": False,
              "native_enforcement_verified": False}
    try:
        connection.request("GET", "/api/security/posture",
                           headers={"Accept": "application/json", "Connection": "close"})
        response = connection.getresponse()
        result["http_status"] = response.status
        # Never consume or print the body, headers, URL redirects or identity.
        response.close()
    except (OSError, http.client.HTTPException):
        result["error"] = "request_failed"
    finally:
        connection.close()
    result["elapsed_ms"] = round((time.monotonic() - start) * 1000)
    print(json.dumps(result, sort_keys=True))
    return 0 if "http_status" in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
