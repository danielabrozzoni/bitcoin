import datetime
import os
import subprocess
import time
import json

# This script sends a GETADDR message to every connected peer and extracts
# received ADDR messages from the debug.log. It outputs the results into CSV files
#
# Requirements:
# - Ensure `bitcoin-cli` is compiled and available at the specified path.
# - Debugging enabled in `bitcoind` configuration.
# - Python 3.x with `subprocess` and `json` modules.

# First time configuration:
# Change parent_dir to match your bitcoin directory (see #TODO below)
# Add to the bitcoin core configuration the node addresses, using connect=

# Before running script:
# Clean debug.log file
# Recompile bitcoind (if there's any changes)
# Start bitcoind and i2pd, bitcoind configuration contains addresses with connect=
# Wait for peers to connect

# TODO: these two variables are hardcoded, change if necessary
BITCOIN_CLI = "../build/src/bitcoin-cli"
LOG_PATH = "/home/daniela/.bitcoin/debug.log"
PARENT_DIR = "/home/daniela/Developer/bitcoin/getaddr-script/data"

peers = {}
now = datetime.datetime.now()
dir = now.strftime("%Y-%m-%d_%H-%M-%S")

path = os.path.join(PARENT_DIR, dir)
os.makedirs(path, exist_ok=True)
print(f'Created data directory {path}')

# Check if the Bitcoin node is running before starting operations.
retries = 10
while retries > 0:
    try:
        result = subprocess.run([BITCOIN_CLI, "getblockchaininfo"], capture_output=True, check=True)
        break
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        time.sleep(1)
        retries -= 1
if retries == 0:
    raise RuntimeError("Bitcoin Core is not running. Exiting...")

print("Bitcoin Core is ok, ready to start")

getpeerinfo_result = subprocess.run([BITCOIN_CLI, "getpeerinfo"], capture_output=True, check=True)
getpeerinfo = json.loads(getpeerinfo_result.stdout)

# Send GETADDR messages to each peer. Retry up to 3 times if sending fails.
for peer in getpeerinfo:
    peer_id = peer['id']
    peer_addr = peer['addr']
    print(f"Sending GETADDR to peer {peer_addr}, id {peer_id}...")
    tries = 0
    while True:
        try:
            tries += 1
            if tries == 3:
                print(f"Error: Failed to send GETADDR to peer {peer_addr} after 3 attempts. Skipping...")
                break
            subprocess.run([BITCOIN_CLI, "sendmsgtopeer", f"{peer_id}", "getaddr", ""], capture_output=True, check=True)
            print("Sent!")
            break
        except:
            print(f"Error: Couldn't send GETADDR to peer {peer_addr}. Retrying...")
            time.sleep(10)
    peers[peer_id] = peer_addr

print("Gathering responses...")
time.sleep(60)

# Extract relevant log data for each peer and save it in a CSV file.
try:
    filtered_lines = []

    # Step 1: Filter the log file for lines containing "GETADDR SCRIPT"
    with open(LOG_PATH, "r") as log_file:
        for line in log_file:
            if "GETADDR SCRIPT" in line:
                filtered_lines.append(line)

    # Step 2: Separate filtered lines by peer addresses
    peer_matches = {peer_id: [] for peer_id in peers}
    for line in filtered_lines:
        for peer_id, peer_addr in peers.items():
            if f"GETADDR SCRIPT{peer_addr}" in line:
                peer_matches[peer_id].append(line)

    # Step 3: Save matching lines for each peer to individual CSV files
    for peer_id, peer_addr in peers.items():
        file_name = f"getaddr-{peer_addr}.csv"
        print(f"Saving matches for peer {peer_addr} to file: {file_name}")
        with open(os.path.join(path, file_name), "w") as output_file:
            output_file.writelines(peer_matches[peer_id])

except Exception as e:
    print(f"Error processing log file: {e}")
