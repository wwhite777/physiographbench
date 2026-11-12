# Distribution and historical provenance

This folder adds 16 complete shared-input scalar records as run.json only.
No weights, per-stay residual arrays, patient records or training logs are included.
JSON string tokens are relocated to repository-relative scientific locators and
private workflow labels are replaced. All numerical, Boolean and null tokens,
array ordering and original fingerprints are unchanged.

Original fingerprints identify the historical input bytes. Distributed file
hashes in manifests/distribution.json and manifests/release_1_3_records.json
identify the public bytes separately. SHA256SUMS checks the merged release.
References to omitted artifacts record provenance and do not imply availability.
The saved-record reader checks scalar summaries and paired arithmetic; it does
not re-evaluate the omitted predictions or checkpoints.
