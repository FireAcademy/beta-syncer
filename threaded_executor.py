from threading import Thread
import time

# each function takes a single argument
# and returns a list of results
# no guarantee given about how results are ordered
class ThreadedExecutor:
	def __init__(self, max_threads=64):
		self.max_threads = max_threads
		self.functions = []
		self.args = []

	def add_function(self, func, arg):
		self.functions.append(func)
		self.args.append(arg)

	def _thread_func(self, func, arg):
		self.running_threads += 1
		a = time.time()
		res = func(arg)
		for elem in res:
			self.results.append(elem)
		print(f"Function took {round(time.time() - a, 3)}s")
		self.running_threads -= 1

	def execute(self):
		self.running_threads = 0
		self.threads = []
		self.results = []
		while len(self.functions) > 0:
			func = self.functions.pop()
			arg = self.args.pop()
			while self.running_threads >= self.max_threads:
				time.sleep(0.1)
			t = Thread(target=self._thread_func, args=(func, arg))
			t.start()
			self.threads.append(t)
		for t in self.threads:
			t.join()
		return self.results
