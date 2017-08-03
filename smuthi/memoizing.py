import pickle


class Memoize:
    def __init__(self, fn):
        self.fn = fn
        self.memo = {}
    def __call__(self, *args, **kwds):
        str = pickle.dumps(args, 1)+pickle.dumps(kwds, 1)
        if not str in self.memo:
            #print("miss") # DEBUG INFO
            self.memo[str] = self.fn(*args, **kwds)
        #else:
            #print("hit") # DEBUG INFO
        #print(len(self.memo))
        return self.memo[str]