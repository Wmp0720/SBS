

"""
        eval 新添加；Tee类用于同时输出到终端和文件
"""

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for s in self.streams:
            s.write(message)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()
