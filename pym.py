import socket
import json
import hashlib
import binascii
import random
import time
import logging

# Configure your Verus address and pool connection
ADDRESS = "RP6jeZhhHiZmzdufpXHCWjYVHsLaPXARt1"
POOL_URL = 'stratum+tcp://na.luckpool.net'
POOL_HOST = 'luckpool.net'
POOL_PORT = 3960

# Set up logging
logging.basicConfig(level=logging.INFO, filename="miner.log", format='%(asctime)s %(message)s')

def logg(msg):
    logging.info(msg)
    print(msg)

def get_job(sock):
    sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')
    response = b''
    while response.count(b'\n') < 2:
        response += sock.recv(1024)
    
    lines = response.decode().split('\n')
    response_json = json.loads(lines[0])
    sub_details = response_json['result']
    extranonce1, extranonce2_size = sub_details[1], sub_details[2]

    sock.sendall(b'{"params": ["' + ADDRESS.encode() + b'", "password"], "id": 2, "method": "mining.authorize"}\n')
    
    response = b''
    while response.count(b'\n') < 4 and not (b'mining.notify' in response):
        response += sock.recv(1024)

    responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip()) > 0 and 'mining.notify' in res]
    job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']
    target = (nbits[2:] + '00' * (int(nbits[:2], 16) - 3)).zfill(64)
    extranonce2 = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(2 * extranonce2_size)

    coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
    coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()

    merkle_root = coinbase_hash_bin
    for h in merkle_branch:
        merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()
    merkle_root = binascii.hexlify(merkle_root).decode()
    merkle_root = ''.join([merkle_root[i] + merkle_root[i + 1] for i in range(0, len(merkle_root), 2)][::-1])

    return job_id, prevhash, merkle_root, version, nbits, ntime, target, extranonce2

def mine():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((POOL_HOST, POOL_PORT))
    logg("Connected to mining pool")

    job_id, prevhash, merkle_root, version, nbits, ntime, target, extranonce2 = get_job(sock)
    logg("Mining job received")

    while True:
        nonce = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(8)
        blockheader = version + prevhash + merkle_root + nbits + ntime + nonce + '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'

        hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(blockheader)).digest()).digest()
        hash_hex = binascii.hexlify(hash_bin).decode()

        if hash_hex < target:
            logg(f"Found a block: {hash_hex}")
            payload = json.dumps({
                "params": [ADDRESS, job_id, extranonce2, ntime, nonce],
                "id": 1,
                "method": "mining.submit"
            }) + '\n'
            sock.sendall(payload.encode())
            response = sock.recv(1024)
            logg(f"Submission response: {response.decode()}")
            break

if __name__ == "__main__":
    mine()
