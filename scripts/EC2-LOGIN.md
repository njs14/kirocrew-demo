# Fresh EC2 Kiro sign-in

Run this from a local interactive terminal after the `kirocrew-demo` SSH alias has been configured:

```sh
python3 scripts/ec2-login.py
```

The helper targets the demo's installed **Kiro CLI 2.21.4** on Ubuntu. It checks remote authentication first and leaves an authenticated account alone. Otherwise, it starts a fresh remote login, captures the CLI's `xdg-open` URL in a private temporary directory, and forwards that login's loopback callback port through SSH. Open the printed URL, choose **GitHub**, and keep the terminal open until it reports authentication. The local Kiro installation is not involved, and credentials or session files are never copied between machines.

This addresses the observed GitHub account flow: forcing the Builder ID device flow returned the browser to sign-in or approval. It is not a claim that every provider or future CLI version uses the same flow. The helper refuses versions other than 2.21.4.

The child CLI omits the inherited `SSH_CLIENT`, `SSH_CONNECTION` and `SSH_TTY` hints so it starts the normal browser flow; the helper supplies the SSH callback tunnel itself. A fresh attempt fails clearly if the CLI has not produced its browser URL within 60 seconds.

The callback port must be free on IPv4 and IPv6 loopback. The helper verifies that its own SSH process owns the listeners before printing the URL. If the port is occupied, stop only the known old login attempt or wait for it to finish, then rerun for a fresh URL. Do not reuse a previous attempt's link.

Ctrl-C cancels only the helper's login process and callback tunnel. Its private temporary files are removed on completion, cancellation or detected disconnect. A hard process kill, host failure or lost network can delay cleanup until the remote timeout (15 minutes by default). Authentication persists in the remote `crew` user's normal Kiro credential store; the helper neither displays nor deletes it. Use `--timeout SECONDS` to change the 60–3600 second limit.

The sign-in URL contains temporary authorization state. The helper requires a terminal and does not write it to a local artifact. Do not paste the URL into the deck, review packets or receipts. Its final status includes only the authentication method, never the account email.
