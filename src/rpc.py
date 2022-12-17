import os
import requests
import time

base_url = os.environ.get("LEAFLET_BASE_URL")

# un0x
def un0x(s):
	return s.replace("0x", "")

def get_remote_sync():
	while True:
		try:
			r = requests.post(f"{base_url}get_blockchain_state")
			peak = r.json()["blockchain_state"]["peak"]
			return peak["height"], un0x(peak["header_hash"]), un0x(peak["prev_hash"])
		except:
			print("Exception while calling get_blockchain_state; sleeping 5s and retrying...")
			time.sleep(5)


def get_remote_block_data_at_height(height):
	while True:
		try:
			r = requests.post(f"{base_url}get_block_record_by_height", json={"height": height})
			block = r.json()["block_record"]
			is_tx_block = block["reward_claims_incorporated"] != None
			return un0x(block["prev_hash"]), un0x(block["header_hash"]), is_tx_block
		except:
			print("Exception while calling get_block_record_by_height; sleeping 5s and retrying...")
			time.sleep(5)
	

def get_block_spends(header_hash):
	while True:
		try:
			r = requests.post(f"{base_url}get_block_spends", json={"header_hash": header_hash})
			data = r.json()
			return data["block_spends"]
		except:
			print("Exception while calling get_block_spends; sleeping 5s and retrying...")
			time.sleep(5)