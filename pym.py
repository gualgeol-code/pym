import socket
import json
import hashlib
import binascii
import random

ADDRESS = "RP6jeZhhHiZmzdufpXHCWjYVHsLaPXARt1"  # Ganti dengan alamat penambang Anda

def logg(message):
    print(message)  # Atau gunakan pustaka logging

def fix_hex_length(hex_str, length=64):
    """ Pastikan string hex memiliki panjang yang diinginkan (dalam byte). """
    return hex_str.zfill(length)

def get_job(sock):
    try:
        # Kirim permintaan mining.subscribe
        logg("Sending mining.subscribe request")
        sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
        response = b''
        while b'\n' not in response:
            response += sock.recv(1024)
        
        logg(f"Raw response after subscribe: {response.decode()}")

        # Parse respons mining.subscribe
        response_json = json.loads(response.decode())
        sub_details = response_json['result']
        
        if len(sub_details) < 2 or sub_details[1] is None:
            raise ValueError("Format respons mining.subscribe tidak terduga")

        extranonce1, extranonce2_size = sub_details[1], 8  # Ukuran default jika tidak disediakan
        
        logg(f"Extranonce1: {extranonce1}, Extranonce2 Size: {extranonce2_size}")

        # Kirim permintaan mining.authorize
        logg("Sending mining.authorize request")
        sock.sendall(json.dumps({
            "params": [ADDRESS, "password"],
            "id": 2,
            "method": "mining.authorize"
        }).encode() + b'\n')

        response = b''
        while b'mining.notify' not in response:
            response += sock.recv(1024)
        
        logg(f"Raw response after authorize: {response.decode()}")

        # Parse respons mining.notify
        responses = [json.loads(res) for res in response.decode().split('\n') if res.strip() and 'mining.notify'
