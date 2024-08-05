import requests
import hashlib
import binascii
import json
import random
import socket
import time
from threading import Thread
import sys
import logging

# Define your Verus address
address = "RP6jeZhhHiZmzdufpXHCWjYVHsLaPXARt1"
# Initialize the current block height
cHeight = 0

def delay_print(s):
    for c in s:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(0.1)

print("Verus Miner Starting...")
cHeight = 0
inpAdd = input('INSERT YOUR VERUS WALLET ADDRESS FOR MINING: ')
address = str(inpAdd)
print(f'\nVerus Wallet Address ===>> {address}')
print('-' * 66)
delay_print('Your Verus Wallet Address Added For Mining Now ...')
print("\n" + '-' * 66)

time.sleep(3)

def logg(msg):
    logging.basicConfig(level=logging.INFO, filename="miner.log", format='%(asctime)s %(message)s')  # include timestamp
    logging.info(msg)

# Function to get the current network block height
def get_current_block_height():
    try:
        r = requests.get('https://blockchain.info/latestblock')
        return int(r.json()['height'])
    except Exception as e:
        logg(f"Error fetching block height: {e}")
        return cHeight

# Function for the mining process
def VerusMiner(restart=False):
    if restart:
        time.sleep(2)
        logg('[*] Verus Miner Restarted')
    else:
        logg('[*] Verus Miner Started')
        print('[*] Verus Miner Started')

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('okeycn-26223.portmap.host', 26223))  # Adjust the pool address and port as needed

    sock.sendall(b'{"id": 1, "method": "mining.subscribe", "params": []}\n')

    lines = sock.recv(1024).decode().split('\n')
    response = json.loads(lines[0])
    sub_details, extranonce1, extranonce2_size = response['result'][:3]

    sock.sendall(b'{"params": ["' + address.encode() + b'", "password"], "id": 2, "method": "mining.authorize"}\n')

    response = b''
    while response.count(b'\n') < 4 and not (b'mining.notify' in response):
        response += sock.recv(1024)

    responses = [json.loads(res) for res in response.decode().split('\n') if len(res.strip()) > 0 and 'mining.notify' in res]
    job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs = responses[0]['params']
    target = (nbits[2:] + '00' * (int(nbits[:2], 16) - 3)).zfill(64)
    extranonce2 = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(2 * extranonce2_size)  # create random

    coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
    try:
        coinbase_hash_bin = hashlib.sha256(hashlib.sha256(binascii.unhexlify(coinbase)).digest()).digest()
    except binascii.Error as e:
        logg(f"Error decoding coinbase: {e}")
        return False

    merkle_root = coinbase_hash_bin
    for h in merkle_branch:
        try:
            merkle_root = hashlib.sha256(hashlib.sha256(merkle_root + binascii.unhexlify(h)).digest()).digest()
        except binascii.Error as e:
            logg(f"Error decoding merkle branch: {e}")
            return False

    merkle_root = binascii.hexlify(merkle_root).decode()
    merkle_root = ''.join([merkle_root[i] + merkle_root[i + 1] for i in range(0, len(merkle_root), 2)][::-1])

    work_on = get_current_block_height()
    print(f'Working on current Network height {work_on}')
    print(f'Current TARGET = {target}')
    z = 0
    while True:
        if cHeight > work_on:
            logg('[*] Restarting Miner')
            VerusMiner(restart=True)
            break

        nonce = hex(random.randint(0, 2 ** 32 - 1))[2:].zfill(8)  # Generate nonce
        blockheader = version + prevhash + merkle_root + nbits + ntime + nonce + \
                      '000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000'
        
        # Debugging: Print blockheader
        print(f"Blockheader: {blockheader}")

        # Validate that the blockheader length is correct
        if len(blockheader) % 2 != 0:
            print("Error: Blockheader length is not even.")
            continue

        try:
            blockheader_bin = binascii.unhexlify(blockheader)
        except binascii.Error as e:
            print(f"Error decoding blockheader: {e}")
            continue

        hash = hashlib.sha256(hashlib.sha256(blockheader_bin).digest()).digest()
        hash = binascii.hexlify(hash).decode()

        if hash.startswith('000000000000000000000'):
            logg(f'hash: {hash}')
        print(f'{str(z)} HASH : {hash}', end='\r')
        z += 1

        if hash < target:
            print('[*] New block mined')
            logg('[*] success!!')
            logg(blockheader)
            logg(f'hash: {hash}')

            payload = bytes(
                '{"params": ["' + address + '", "' + job_id + '", "' + extranonce2 \
                + '", "' + ntime + '", "' + nonce + '"], "id": 1, "method": "mining.submit"}\n', 'utf-8')
            sock.sendall(payload)
            logg(payload)
            ret = sock.recv(1024)
            logg(ret)

            return True

# Function to listen for new blocks
def newBlockListener():
    global cHeight

    while True:
        network_height = get_current_block_height()

        if network_height > cHeight:
            logg(f'[*] Network has new height {network_height}')
            logg(f'[*] Our local is {cHeight}')
            cHeight = network_height
            logg(f'[*] Our new local after update is {cHeight}')

        # respect Api
        time.sleep(40)

# Main function to start the miner and block listener
if __name__ == '__main__':
    # Start the block listener and miner threads
    Thread(target=newBlockListener).start()
    time.sleep(2)
    Thread(target=VerusMiner).start()
