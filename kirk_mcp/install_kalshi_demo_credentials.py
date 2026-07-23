"""Install Kalshi DEMO credentials directly into fixed macOS Keychain entries.

The private key is passed to Security.framework in memory, never through a
subprocess argument or output stream.
"""

from __future__ import annotations

import argparse
import ctypes
import getpass
import sys
from pathlib import Path
from typing import Optional, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kirk_mcp.kalshi_demo import (
    KEYCHAIN_ACCOUNT,
    KEYCHAIN_API_KEY_SERVICE,
    KEYCHAIN_PRIVATE_KEY_SERVICE,
)

_SECURITY_FRAMEWORK = "/System/Library/Frameworks/Security.framework/Security"
_DUPLICATE_ITEM = -25299
_ITEM_NOT_FOUND = -25300


def _add_generic_password(service: str, secret: bytes) -> int:
    security = ctypes.CDLL(_SECURITY_FRAMEWORK)
    add_password = security.SecKeychainAddGenericPassword
    add_password.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    add_password.restype = ctypes.c_int32

    service_bytes = service.encode("utf-8")
    account_bytes = KEYCHAIN_ACCOUNT.encode("utf-8")
    service_buffer = ctypes.create_string_buffer(service_bytes)
    account_buffer = ctypes.create_string_buffer(account_bytes)
    secret_buffer = ctypes.create_string_buffer(secret)
    return int(
        add_password(
            None,
            len(service_bytes),
            ctypes.cast(service_buffer, ctypes.c_void_p),
            len(account_bytes),
            ctypes.cast(account_buffer, ctypes.c_void_p),
            len(secret),
            ctypes.cast(secret_buffer, ctypes.c_void_p),
            None,
        )
    )


def _find_generic_password(service: str, item_ref: Optional[ctypes.c_void_p] = None) -> int:
    security = ctypes.CDLL(_SECURITY_FRAMEWORK)
    find_password = security.SecKeychainFindGenericPassword
    find_password.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    find_password.restype = ctypes.c_int32

    service_bytes = service.encode("utf-8")
    account_bytes = KEYCHAIN_ACCOUNT.encode("utf-8")
    service_buffer = ctypes.create_string_buffer(service_bytes)
    account_buffer = ctypes.create_string_buffer(account_bytes)
    return int(
        find_password(
            None,
            len(service_bytes),
            ctypes.cast(service_buffer, ctypes.c_void_p),
            len(account_bytes),
            ctypes.cast(account_buffer, ctypes.c_void_p),
            None,
            None,
            ctypes.byref(item_ref) if item_ref is not None else None,
        )
    )


def _delete_generic_password(service: str) -> int:
    security = ctypes.CDLL(_SECURITY_FRAMEWORK)
    item_ref = ctypes.c_void_p()
    status = _find_generic_password(service, item_ref)
    if status != 0:
        return status
    delete_item = security.SecKeychainItemDelete
    delete_item.argtypes = [ctypes.c_void_p]
    delete_item.restype = ctypes.c_int32
    return int(delete_item(item_ref))


def _validate_private_key(pem: bytes) -> None:
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except (TypeError, ValueError):
        raise ValueError("the selected file is not an unencrypted PEM private key")
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("the selected file is not an RSA private key")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install fixed Kalshi DEMO credentials in macOS Keychain"
    )
    parser.add_argument(
        "--private-key-file",
        required=True,
        type=Path,
        help="path to the downloaded DEMO .key file (never use a production key)",
    )
    args = parser.parse_args(argv)

    if sys.platform != "darwin":
        parser.error("this local candidate installer runs only on macOS; its candidate credential store is macOS Keychain")

    confirmation = input(
        "Type PERSONAL DEMO to confirm this is the captain's personal demo account (never live/corporate): "
    )
    if confirmation != "PERSONAL DEMO":
        parser.error("personal DEMO confirmation did not match; nothing installed")

    key_id = getpass.getpass("Personal Kalshi DEMO API key ID (hidden; not a login identifier): ").strip()
    if not key_id:
        parser.error("DEMO API key ID cannot be empty")
    try:
        private_key_pem = args.private_key_file.read_bytes()
        _validate_private_key(private_key_pem)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    entries = (
        (KEYCHAIN_API_KEY_SERVICE, key_id.encode("utf-8")),
        (KEYCHAIN_PRIVATE_KEY_SERVICE, private_key_pem),
    )

    for service, _ in entries:
        status = _find_generic_password(service)
        if status == 0:
            print(
                "DEMO Keychain entry already exists: %s; remove every fixed entry explicitly before reinstalling"
                % service,
                file=sys.stderr,
            )
            return 1
        if status != _ITEM_NOT_FOUND:
            print(
                "DEMO Keychain lookup failed for entry %s (OSStatus %d); no credential value printed"
                % (service, status),
                file=sys.stderr,
            )
            return 1

    installed = []
    for service, secret in entries:
        status = _add_generic_password(service, secret)
        if status != 0:
            for done in installed:
                _delete_generic_password(done)
            detail = (
                "another entry appeared concurrently"
                if status == _DUPLICATE_ITEM
                else "OSStatus %d" % status
            )
            print(
                "DEMO Keychain installation failed for entry %s (%s); no credential value printed and any partial entry was rolled back"
                % (service, detail),
                file=sys.stderr,
            )
            return 1
        installed.append(service)

    print("Installed personal Kalshi DEMO credentials in macOS Keychain.")
    print("account role label (not a login identifier): " + KEYCHAIN_ACCOUNT)
    print("services: " + KEYCHAIN_API_KEY_SERVICE + ", " + KEYCHAIN_PRIVATE_KEY_SERVICE)
    print("Credential values were not printed. Remove the downloaded key file securely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
