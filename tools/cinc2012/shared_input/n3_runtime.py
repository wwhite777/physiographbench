"""Reuse public clinical data/metric/model bodies, extending only the cap guard."""
from n3_common import *
import importlib.util
import types
sys.path.insert(0,str(PROJECT/'tools/cinc2012'))
import cinc2012_common as clinical_base
v4=clinical_base.v4
sys.path.insert(0,str(PROJECT/'experiments/shared_input_primary'))
from n2_common import load_shared
shared=load_shared()
path=PROJECT/'tools/v4_protocol.py'
code=path.read_text()
if code.count('if not 1 <= epochs <= 35:')!=1: raise ValueError('Changed epoch validation')
training=types.ModuleType('_shared_cinc2012_training')
training.__file__=str(path)
sys.modules[training.__name__]=training
exec(compile(code.replace('if not 1 <= epochs <= 35:','if not 1 <= epochs <= 105:').replace('epoch budget must be between 1 and 35','epoch budget must be between 1 and 105'),str(path),'exec'),training.__dict__)

def within_data(npz=None,C=12,K=12,batch=128,seed=0,max_stays=None,min_length=0):
    if (C,K,min_length)!=(12,12,0): raise ValueError('Frozen C=K=12, length>=24')
    loaders,meta=clinical_base.make_data(npz,'within',batch,seed,max_stays)
    return [loaders['train'],loaders['val'],None,loaders['testB']],meta

def shared_factory(name,sizes,variant):
    if name!='physiograph_gru_shared' or variant not in ('none','admissible'): raise ValueError('Unsupported model')
    return shared.build_arm(variant,sizes)
training.make_data=within_data
training.build=shared_factory
