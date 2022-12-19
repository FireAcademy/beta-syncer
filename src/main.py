from chia.types.blockchain_format.program import Program
from chia.util.condition_tools import parse_sexp_to_conditions, conditions_by_opcode
from chia.types.condition_opcodes import ConditionOpcode
from chia.wallet.puzzles.singleton_top_layer_v1_1 import SINGLETON_LAUNCHER_HASH, SINGLETON_MOD_HASH
from clvm.casts import int_from_bytes
from threaded_executor import ThreadedExecutor
from chia_rs import Coin
from models import *
from rpc import *
from db import *
import time
import threading

def get_last_sync():
	last_from_db = get_last_block_from_db()
	if last_from_db == None:
		return 2000000, None # 2170000 is 2 days before NFT1 announcement
	
	return last_from_db.height, last_from_db.header_hash


def hex2bytes(h):
	return bytes.fromhex(h.replace('0x', ''))


def get_coin_id(coin_json):
	c = Coin(
		parent_coin_info=hex2bytes(coin_json["parent_coin_info"]),
		puzzle_hash=hex2bytes(coin_json["puzzle_hash"]),
		amount=coin_json["amount"]
	)
	return c.name().hex()


def process_block_spend(height, header_hash, spend):
	spent_coin = spend["coin"]
	spent_coin_parent_coin_info = un0x(spent_coin["parent_coin_info"])
	spent_coin_puzzle_hash = un0x(spent_coin["puzzle_hash"])
	spent_coin_amount = spent_coin["amount"]
	spent_coin_id = get_coin_id(spent_coin)

	puzzle_reveal = Program.fromhex(un0x(spend["puzzle_reveal"]))
	solution = Program.fromhex(un0x(spend["solution"]))

	solution_as_list = []
	try:
		solution_as_list = [_ for _ in solution.as_iter()]
	except:
		pass

	# Minting
	if spent_coin_puzzle_hash == SINGLETON_LAUNCHER_HASH:
		if len(solution_arr) < 2:
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		new_singleton_puzzle_hash = solution_as_list[0].as_atom().hex()
		new_singleton_amount = solution_as_list[1].as_int()
		new_singleton_coin_json = {
			"parent_coin_info": spent_coin_id,
			"puzzle_hash": new_singleton_puzzle_hash,
			"amount": new_singleton_amount
		}
		return [
			SingletonState(
				coin_id = get_coin_id(new_singleton_coin_json),
				header_hash = header_hash,
				height = height,
				parent_coin_id = spent_coin_id,
				puzzle_hash = new_singleton_puzzle_hash,
				amount = new_singleton_amount,
				launcher_id = spent_coin_id,
				inner_puzzle_hash = None,
				melted = False,
			)
		]

	# Singleton puzzle running
	uncurried_puzzle_reveal, uncurried_args_program = puzzle_reveal.uncurry()
	if uncurried_puzzle_reveal.get_tree_hash() == SINGLETON_MOD_HASH:
		uncurried_args = [_ for _ in uncurried_args_program.as_iter()]
		if len(uncurried_args) != 2:
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		singleton_struct = uncurried_args[0]
		inner_puzzle = uncurried_args[1]

		inner_puzzle_hash = str(inner_puzzle.get_tree_hash())

		singleton_mod_hash_program, launcher_info_program = singleton_struct.as_pair()
		singleton_mod_hash = singleton_mod_hash_program.as_atom().hex()

		if singleton_mod_hash != str(SINGLETON_MOD_HASH): # str(bytes32)
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		launcher_id_program, launcher_puzzle_hash_program = launcher_info_program.as_pair()
		launcher_id = launcher_id_program.as_atom().hex()
		launcher_puzzle_hash = launcher_puzzle_hash_program.as_atom().hex()
		
		if launcher_puzzle_hash != str(SINGLETON_LAUNCHER_HASH): # str(bytes32)
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		if len(solution_as_list) != 3:
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		inner_solution = solution_as_list[2]
		inner_output_conditions_program = inner_puzzle.run(inner_solution)

		err, inner_output_conditions = parse_sexp_to_conditions(inner_output_conditions_program)
		if err != None:
			print(f"ERR? {height} {header_hash} {spend}")
			return []

		inner_output_conditions_dict = conditions_by_opcode(inner_output_conditions)
		create_coin_inner_conditions = inner_output_conditions_dict[ConditionOpcode.CREATE_COIN]
		for create_coin_inner_condition in create_coin_inner_conditions:
			parameters = create_coin_inner_condition.vars
			if len(parameters) not in [2, 3]: # optional memo
				continue

			new_singleton_inner_puzzle_hash = parameters[0]
			new_coin_amount = int_from_bytes(parameters[1])

			# there's only one odd value
			if new_coin_amount % 2 == 0:
				continue

			if new_coin_amount == -113: # MELT!
				return [
					SingletonState(
						coin_id = spent_coin_id,
						header_hash = header_hash,
						height = height,
						parent_coin_id = spent_coin_parent_coin_info,
						puzzle_hash = spent_coin_puzzle_hash,
						amount = spent_coin_amount,
						launcher_id = launcher_id,
						inner_puzzle_hash = inner_puzzle_hash,
						melted = True,
					),
					Puzzle(
						puzzle_hash = inner_puzzle_hash,
						puzzle = bytes(inner_puzzle),
					)
				]
			else:
				# This is a 'transfer' (current coin gets spent, singleton layer persists)
				# easiest way to get puzzle hash is to just watch the output conditions

				output_conditions_program = puzzle_reveal.run(solution)
				err, output_conditions = parse_sexp_to_conditions(output_conditions_program)
				if err != None:
					print(f"ERR? {height} {header_hash} {spend}")
					return []

				output_conditions_dict = conditions_by_opcode(output_conditions)
				create_coin_output_conditions = output_conditions_dict[ConditionOpcode.CREATE_COIN]

				new_coin_puzzle_hash = None
				for create_coin_output_condition in create_coin_output_conditions:
					condition_output_amount = int_from_bytes(create_coin_output_condition.vars[1])

					if new_coin_amount == condition_output_amount:
						new_coin_puzzle_hash = create_coin_output_condition.vars[0].hex()

				new_coin_json = {
					"parent_coin_info": spent_coin_id,
					"puzzle_hash": new_coin_puzzle_hash,
					"amount": new_coin_amount
				}
				new_coin_id = get_coin_id(new_coin_json)

				return [
					# 1. Spent coin revealed singleton inner puzzle
					Puzzle(
						puzzle_hash = inner_puzzle_hash,
						puzzle = bytes(inner_puzzle),
					),
					# 2. This is a transfer, so a new coin for the singleton was also created
					SingletonState(
						coin_id = new_coin_id,
						header_hash = header_hash,
						height = height,
						parent_coin_id = spent_coin_id,
						puzzle_hash = new_coin_puzzle_hash,
						amount = new_coin_amount,
						launcher_id = launcher_id,
						inner_puzzle_hash = inner_puzzle_hash,
						melted = False,
					)
				]

		return []

	return []


def process_block(height, header_hash):
	start_time = time.time()
	objects_to_add = [SyncedBlock(height=height, header_hash=header_hash)]
	
	block_spends = get_block_spends(header_hash)
	
	puzzles_to_add = []
	for spend in block_spends:
		res = process_block_spend(height, header_hash, spend)
		for elem in res:
			if isinstance(elem, Puzzle):
				puzzles_to_add.append(elem)
			else:
				objects_to_add.append(elem)

	if len(puzzles_to_add) > 0:
		add_puzzles_to_db_now(puzzles_to_add)
	if len(objects_to_add) > 0:
		add_objects_to_db_now(objects_to_add)
	print(f"Processed block #{height} ({len(block_spends)} spends) in {round(time.time() - start_time, 3)}s")


def main():
	synced_height, synced_hash = get_last_sync()
	leaflet_height, leaflet_hash, leaflet_prev_hash = get_remote_sync()
	
	if synced_hash == None:
		height_to_add_to_db = max(synced_height - 1, 0)
		prev_hsh, hsh, is_tx_block = get_remote_block_data_at_height(height_to_add_to_db)
		add_object_to_db_now(SyncedBlock(height=height_to_add_to_db, header_hash=hsh))
		synced_height, synced_hash = get_last_sync()

	while True:
		if synced_height == leaflet_height:
			time.sleep(5)
			leaflet_height, leaflet_hash, leaflet_prev_hash = get_remote_sync()
		elif synced_height < leaflet_height:
			while synced_height < leaflet_height:
				height_to_process = synced_height + 1
				remote_prev_hash, hash_to_process, is_tx_block = get_remote_block_data_at_height(height_to_process)
				
				if synced_hash != remote_prev_hash:
					print(f"Something is fishy at height {synced_height} - dropping block.")
					print(synced_height, synced_hash, remote_prev_hash, height_to_process)
					synced_height, synced_hash = get_synced_block_from_db(synced_height - 1)
					drop_sync_block_from_db(height_to_process)
					continue
				
				if is_tx_block:
					process_block(height_to_process, hash_to_process)
				else:
					add_object_to_db_now(SyncedBlock(height=height_to_process, header_hash=hash_to_process))

				synced_height, synced_hash = height_to_process, hash_to_process
		else:
			print("Leaflet is somehow behind our height...")
			print("Sleeping 1 min; hopefully it will figure it out by the time I wake up")
			time.sleep(60)
			leaflet_height, leaflet_hash, leaflet_prev_hash = get_remote_sync()


if __name__ == "__main__":
	main()