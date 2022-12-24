
class ConfigDict(dict):
    def __getattr__(self, key):
        if key in self.keys():
            return super().__getitem__(key)
        else:
            return getattr(super(), key)

    # def __setattr__(self, key, value):
    #     try:
    #         getattr(super(), key)
    #     except AttributeError:
    #         if isinstance(value, dict):
    #             self[key] = self.get(key, ConfigDict()).update(value)
    #         else:
    #             super().__setitem__(key, value)
    #     else:
    #         setattr(super(), key, value)
    #
    # def __delattr__(self, key):
    #     if key in self.keys():
    #         del self[key]
    #     else:
    #         super().__delattr__(key)

    def update(self, u):
        for k, v in u.items():
            if isinstance(v, dict):
                self[k] = self.get(k, ConfigDict())
                self[k].update(v)
            else:
                self[k] = v
        return self

    def printToStdout(self):
        import pprint
        pprint.pp(self)

    def copy(self):
        from copy import deepcopy
        return deepcopy(self)

