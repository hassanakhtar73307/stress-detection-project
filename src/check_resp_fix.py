from preprocess import filter_chest_signals
from load_wesad import load_subject
import numpy as np

d = load_subject('S2')
filtered = filter_chest_signals(d['chest'])
print('Resp NaN count:', np.isnan(filtered['Resp']).sum(), '/', len(filtered['Resp']))
print('Resp sample values:', filtered['Resp'][:5])