from models import *
from sqlalchemy.dialects.postgresql import insert

def get_last_block_from_db() -> SyncedBlock:
	syncedBlock = None
	with Session() as sess:
		syncedBlock = sess.query(SyncedBlock).order_by(SyncedBlock.height.desc()).limit(1).first()
		sess.close()
	return syncedBlock

def get_synced_block_from_db(height) -> SyncedBlock:
	syncedBlock = None
	with Session() as sess:
		syncedBlock = sess.query(SyncedBlock).where(SyncedBlock.height == height).limit(1).first()
		sess.close()
	return height, syncedBlock.header_hash

def drop_sync_block_from_db(height):
	with Session() as sess:
		syncedBlock = sess.query(SyncedBlock).where(SyncedBlock.height == height).delete()
		sess.commit()
		sess.close()

def add_object_to_db_now(obj):
	with Session() as sess:
		sess.add(obj)
		sess.commit()
		sess.close()

def add_objects_to_db_now(objs):
	with Session() as sess:
		sess.add_all(objs)
		sess.commit()
		sess.close()

def add_puzzles_to_db_now(puzzles):
	with Session() as sess:
		statement = insert(Puzzle).values([{
			'puzzle_hash': p.puzzle_hash,
			'puzzle': p.puzzle
		} for p in puzzles]).on_conflict_do_nothing()
		sess.execute(statement)
		sess.commit()
		sess.close()

def get_puzzle_from_db(puzz_hash):
	puzzle = None
	with Session() as sess:
		syncedBlock = sess.query(Puzzle).where(Puzzle.puzzle_hash == puzz_hash).limit(1).first()
		sess.close()
	return puzzle