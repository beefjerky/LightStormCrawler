import time
from Logger import INFO, ERR, DBG

stats = dict((k, {'i': 0, 't': 0}) for k in ['page', 'job'])

stats['page']['err'] = {'tamper': 0, 'network': 0, 'decode': 0, 'flood': 0, 'giveup': 0, 'nocontent': 0}

stats['job']['err'] = {'exception': 0, 'notfound': 0}

crawler= {}


