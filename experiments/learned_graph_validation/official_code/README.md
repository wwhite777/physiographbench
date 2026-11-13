# GraFITi official-code attempt

This record preserves one attempt with the authors' official code at source
commit `698060bb0e9385d79eaf41b7981a05390725a1e5`, fold 0, the P12 36-hour
interpolation setup. It exited 1 while constructing the dataset/encoder, before
model fitting, with `KeyError: 'Time'`. The cause was not diagnosed. This is
neither a successful official-code reproduction nor evidence that the published
method fails. No test metric was obtained and no score enters the benchmark.

The sanitized record and complete sanitized log retain commands, versions,
source/data fingerprints, traceback and exit status. Original and distributed
log hashes differ because paths were sanitized upstream; `_distribution` in
the record distinguishes them. Code, environments and patient files from this
attempt are not redistributed. The separate paper-based adaptation and fixed
graph experiments remain described in the parent folder.
