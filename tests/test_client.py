"""Testy parsování stavu z myčky (skutečné odpovědi modulu)."""

from candy_netscan.client import parse_status, xor_decrypt, xor_encrypt
from candy_netscan.find_key import recover_key

# Výřez skutečné odpovědi během čištění (P12): firmware neescapuje zpětné lomítko v r9.
CLEANING_STATUS = (
    '{\n\t"statusDWash":{\n\t\t"StatoDWash":"3",\n\t\t"Program":"P2",\n'
    '\t\t"r9":"H_2 \\",\n\t\t"r15":"1"\n\t}\n}'
)


def test_unescaped_backslash_from_firmware():
    fields = parse_status(CLEANING_STATUS)
    assert fields["r9"].startswith("H_2")
    assert (fields["StatoDWash"], fields["r15"]) == ("3", "1")


def test_recover_key_from_known_prefix():
    key = "Ab3$xY9!qW7#zK2%"
    assert recover_key(xor_encrypt(CLEANING_STATUS.replace("\\", ""), key)) == key


def test_xor_roundtrip():
    key = "0123456789abcdef"
    assert xor_decrypt(xor_encrypt("Reset=1", key), key) == "Reset=1"
