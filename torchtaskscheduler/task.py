import multiprocessing as mp
import multiprocessing.connection as conn
import os
import sys
import logging
import importlib
import ctypes
from typing import Any

import torch

def task_func(connection: conn.Connection, device: int, working_dir: str,
              module_name: str, function_name: str, args: tuple[Any], kwargs: dict[str, Any]):
    os.makedirs(working_dir, exist_ok=True)
    old_cwd = os.getcwd()
    os.chdir(working_dir)
    sys.path.insert(0, old_cwd)
    sys.stdout = open(os.path.join("output.txt"), "w")
    sys.stderr = open(os.path.join("error.txt"), "w")

    try:
        device = torch.device("cuda:{}".format(device))
        kwargs["device"] = device
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        result = func(*args, **kwargs)
        if result is not None:
            connection.send(result)
        else:
            connection.send(0) # placeholder value
    except Exception as e:
        logging.error("An error occurred", exc_info=True)
        connection.send(-1) # error occurred
    sys.stdout.flush()
    sys.stdout.close()
    sys.stderr.flush()
    sys.stderr.close()

class Task:
    def __init__(self, device: int, working_dir: str, proc_id: int,
                 module_name: str, function_name: str, args: tuple[Any], kwargs: dict[str, Any]):
        self.device = device
        self.working_dir = working_dir
        self.args = args
        self.kwargs = kwargs

        self.connection, child_connection = mp.Pipe()
        self.process = mp.Process(target=task_func, name="TaskProcess-{}".format(proc_id),
                                  args=(child_connection, device, working_dir, module_name, function_name, args, kwargs))
    
    def start(self):
        self.process.start()
    
    def is_alive(self):
        return self.process.is_alive()
    
    def get_result(self):
        return self.connection.recv()
