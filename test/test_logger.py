import pytest
import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import logger
from logger import Category as C

def test_file_ptr_valid():
    os.makedirs("log", exist_ok=True)
    logvalid = logger.LogFileCtx("log", "log.log")

    fp_valid = logvalid.getFileFp()

    assert(fp_valid != None)

    logvalid.close()
    del logvalid
    shutil.rmtree("log")

def test_log_write():
    os.makedirs("log", exist_ok=True)

    log_ctx = logger.Logger("parser")
    log_ctx.log(C.INFO, "INFO test msg")
    log_ctx.log(C.WARN, "WARN test msg")
    log_ctx.log(C.ERR, "ERROR test msg")

    contents = []
    with open("./log/log", "r", encoding="utf8") as f:
        for line in f:
            contents.append(line)
    
    for i in range(len(contents)):
        content = contents[i]
        print(content)
        assert(len(content) > 0)
    
    del log_ctx
