# Baseline implementations and declared adaptations

These are local implementations of published architectures adapted to the same
hourly forecasting interface. They do not import or redistribute an upstream
implementation. The scores measure these declared ports on this cohort and do
not reproduce the papers' original dataset scores. The source files retain the
actual tensor operations; this note explains decisions needed to interpret them.

## t-PatchGNN

Weijia Zhang, Chenlong Yin, Hao Liu, Xiaofang Zhou and Hui Xiong,
*Irregular Multivariate Time Series Forecasting: A Transformable Patching Graph
Neural Networks Approach* (2024).

`tpatchgnn_adapter.py` implements transformable time-aware patch convolution,
within-variable Transformer attention, a patient/patch-specific learned directed
variable graph, graph message passing, and a future-time query decoder. The graph
is learned from variable embeddings and patch states and does not receive organ
edges. Missing observations are excluded from the patch-member softmax.

The default width is 64, with 8-hour patch width and stride, 10-dimensional time
and graph embeddings, one attention head, one graph hop, and one intra/inter
block. A 12-hour context has two patches; the terminal patch contains only the
four available context hours and never receives future observations. These
settings give 357,682 trainable parameters. The time embedding contains one
affine coordinate and nine learned sinusoidal coordinates. The patch decoder
flattens chronological patch states, projects to width 64, and combines them with
future-time embeddings in a shared multilayer perceptron.

The paper's sub-hourly timestamps are unavailable in this hourly cohort. Packed
masked tensors represent observed-member lists. The implementation explicitly
chooses a post-convolution offset and rectified linear unit (ReLU), and an empty
patch has the resulting learned empty-content representation with a zero
presence flag. The default single-block setup makes the between-block residual
convention inactive. Static covariates are ignored. The benchmark trains with
pooled masked mean squared error (MSE) rather than the paper's per-variable query
averaging, and uses validation-selected checkpoints under the common 35-epoch
cap. These choices are adaptations, not tuned variants selected on external B.

## GraFITi

*GraFITi: Graphs for Forecasting Irregularly Sampled Time Series* (2024).

`grafiti_adapter_v3.py` builds a bipartite graph between variables and time
points. Available observations are edges with value/presence features; all future
hour/feature queries are edges with zero query features. Future labels and future
availability masks do not enter graph construction. Incident multi-head attention
updates both node types through the same attention block within a layer, then
updates edge states. Final query-edge scalar states are the predictions.

The port uses width 64, four attention heads and two graph layers, giving 43,400
parameters. The paper requires scalar final states but leaves the width transition
unspecified. Separate affine maps project variable/time nodes and edge states to
scalars before the final layer; internal attention retains width 64. This is an
explicit dimensional completion with a scalar bottleneck. The residual uses the
actual input query, not its learned attention projection.

The paper leaves its nonlinear activation unspecified. This port uses LeakyReLU
with negative slope 0.1 in both activated attention residuals and in the edge
update residual. This retains gradients and signed scalar forecasts; a previous
ReLU implementation collapsed at the scalar output. The slope was chosen from
that mechanism without a slope search on external performance. Dense masked
storage preserves the finite-value graph operations but does not provide sparse
computational cost. Isolated context-time nodes cannot transmit to query edges.

Training averages observed query errors within each nonempty example and then
averages examples. Pooled evaluation weights observations differently. Complete
query risk is unobservable because targets are missing. The port uses the frozen
hourly windows, A-train normalization, Adam at 0.001, weight decay 0.00001,
cosine scheduling, gradient clipping at 1, maximum 35 epochs, patience 8 and
minimum validation improvement 0.0001. Static covariates are ignored. These are
benchmark adaptations rather than the original paper's cohorts and folds.

`registry_v3.py` and `cinc_port_runner_v3.py` are the published clinical route.
The included v2 registry/adapter is retained as a compatibility dependency and
is not used by the experiment plan for reported GraFITi results.

## Counterfactual Recurrent Network (CRN)

Ioana Bica and colleagues, *Estimating Counterfactual Treatment Outcomes over
Time Through Adversarially Balanced Representations* (2020).

`crn_full_v2.py` is an encoder–decoder adaptation for continuous simulated dose.
The outcome heads use the original dose, while ten equal-width dose classes on
[0, 0.5] provide the adversarial balancing labels. Gradient reversal multiplies
the representation gradient by the negative balancing coefficient. Ordinary
representation dropout is used; variational recurrent dropout and uncertainty
fitting are not implemented. This is a declared difference from the paper.

The encoder's balanced representation initializes the decoder hidden state;
decoder cell memory starts at zero. Fitting uses observed outcome feedback,
while inference uses its own predicted outcomes. Dose arrays in this simulator
are indexed by response endpoints, so the encoder receives prior treatment,
not the treatment classified by its own representation. The outcome loss sums
time and coordinates before averaging trajectories, while balancing loss uses
the recorded treatment classification scale. The logistic schedule uses the
literal one-based epoch and restarts in each stage.

The default 60-epoch budget is divided equally between encoder and decoder,
with Adam at 0.002, batch size 128, and gradient clipping at 1. The sweep uses
maximum balancing weights 0, 0.25 and 1, three specified policy cells and four
seeds; the zero-weight arm explicitly retains the full architecture. A separate
zero-weight arm doubles the budget to 120 epochs at the identifiable cell.
The full adaptation underfits that positive control. Its failure cannot establish
an identification failure in an otherwise identifiable regime. CRN-lite remains
a separate balancing surrogate and is labelled separately throughout the results.

## Common scope

Both learned variable graphs use paper settings without a tuning grid. The
recurrent clinical comparators use validation-only equal-count tuning. All
clinical scores use the same masks and cohort split, but training objectives
can differ as disclosed above. Computational cost, parameter count and original
paper protocols are not equalized by a common epoch cap. Consult the frozen run
JSONs for each actual configuration and seed.
