"""
logger class
"""

import os
from datetime import datetime
from typing import List, Literal
from enum import Enum

class Category(Enum):
    INFO = "I"
    WARN = "W"
    ERR  = "E"


class LogFileCtx():
    """
    singleton
    """
    _instance_ = None

    def __new__(cls, *args, **kwargs):
        if cls._instance_ is None:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self, root_path:str, file_name: str) -> None:
        self.file_name_ = file_name
        self.root_path_ = root_path
        self.file_path_ = os.path.join(self.root_path_, self.file_name_)
        self.fp = None
        
        if not os.path.exists(self.file_path_):
            os.makedirs(os.path.dirname(self.file_path_), exist_ok=True)

            with open(self.file_path_, mode="w", encoding="utf8") as f:
                f.write("")

        if os.path.exists(self.file_path_):
            self.fp = open(self.file_path_, mode="a+", encoding="utf8")
            
    def __del__(self):
        print("delete LogFileCtx instance")
        if self.fp:
            self.fp.close()
    
    def getFileFp(self):
        return self.fp

    def close(self):
        try:
            if self.fp:
                self.fp.close()
        finally:
            return 

class _Logger():
    def __init__(self, module: str, fp) -> None:
        self.module_ = module
        self.fp_ = fp
    
    def log(self, 
            category: Literal[Category.INFO, Category.WARN, Category.ERR], 
            msg: str):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{time}] [{self.module_}] [{category.value}] {msg}\n"
        if self.fp_:
            self.fp_.write(message)

        print(message) # console

class Logger():
    def __init__(self, module:str) -> None:
        self.log_ctx = LogFileCtx("log", "log")
        fp = self.log_ctx.getFileFp()
        self.log_ctx = _Logger(module, fp)
    
    def log(self, 
            category: Literal[Category.INFO, Category.WARN, Category.ERR], 
            msg: str):
        self.log_ctx.log(category, msg)