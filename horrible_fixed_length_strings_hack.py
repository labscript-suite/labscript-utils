import h5py

def horribly_hack_fixed_length_strings():
    _guess_dtype = h5py._hl.base.guess_dtype

    def guess_dtype(data):
        if type(data) not in [bytes, unicode]:
            return _guess_dtype(data)
            
    # I feel dirty:
    h5py._hl.base.guess_dtype = guess_dtype
