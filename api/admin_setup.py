"""One-time admin credential setup. Run on the server:

    python -m api.admin_setup

Prompts for a username and password (entered by you, never stored in plain
text) and generates a TOTP secret for two-factor auth. A QR code is printed in
the terminal: scan it with Google Authenticator / Authy. The secret stays on
the server. Re-run any time to reset the credentials.
"""

from __future__ import annotations

import getpass
import sys

import pyotp
import qrcode

from api import store

ISSUER = "CloudPull"


def main() -> None:
    store.init()
    print("== CloudPull admin setup ==")
    user = input("Admin username: ").strip()
    if not user:
        print("Username cannot be empty.")
        sys.exit(1)

    pw1 = getpass.getpass("Admin password: ")
    pw2 = getpass.getpass("Repeat password: ")
    if pw1 != pw2 or not pw1:
        print("Passwords do not match or are empty.")
        sys.exit(1)
    if len(pw1) < 8:
        print("Use at least 8 characters.")
        sys.exit(1)

    secret = pyotp.random_base32()
    store.set_admin(user, pw1, secret)

    uri = pyotp.TOTP(secret).provisioning_uri(name=user, issuer_name=ISSUER)
    print("\nScan this QR in your authenticator app (Google Authenticator, Authy, ...):\n")
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.print_ascii(invert=True)
    print(f"\nIf you cannot scan, enter this secret manually: {secret}")
    print("\nDone. Open https://cloudpull.cloud/admin and log in with your")
    print("username, password and the 6-digit code from the app.")


if __name__ == "__main__":
    main()
