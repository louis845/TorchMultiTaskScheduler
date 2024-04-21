import multiprocessing as mp

assert mp.get_start_method() == "spawn", "Please use spawn start method"