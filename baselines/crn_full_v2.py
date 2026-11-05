"""CRN with teacher-forced fitting and autoregressive outcome feedback.

Paper §4, Fig.2 and Appendix E are the specification. Continuous CVSim doses
remain an adaptation: ten equal-width treatment classes on [0,.5] for balancing,
original doses for the outcome heads. Ordinary representation dropout remains
a declared deviation from variational recurrent dropout and uncertainty fitting.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import math
import sys

import torch
from torch import nn
from torch.nn import functional as F

from port_utils_v2 import PROJECT

sys.dont_write_bytecode = True
if str(PROJECT / 'src') not in sys.path:
    sys.path.insert(0, str(PROJECT / 'src'))


class _Reverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, representation, coefficient):
        ctx.coefficient = coefficient
        return representation.view_as(representation)

    @staticmethod
    def backward(ctx, gradient):
        return -ctx.coefficient * gradient, None


def grad_reverse(representation, coefficient):
    return _Reverse.apply(representation, coefficient)


def balancing_coefficient(epoch, maximum=1.0):
    """Appendix E Algorithm 1, literal p=1,...,max_epochs, without rescaling p."""
    if epoch < 0 or maximum < 0:
        raise ValueError('Require nonnegative epoch and maximum')
    return maximum * (2 / (1 + math.exp(-10 * epoch)) - 1)


def trajectory_outcome_loss(prediction, target):
    """Eq. (3), Appendix E: coordinate/time sums, then mean trajectories."""
    return (prediction - target).square().flatten(1).sum(1).mean()


def _head(input_dim, hidden_dim, output_dim):
    return nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ELU(),
                         nn.Linear(hidden_dim, output_dim))


class CRNFull(nn.Module):
    """Two-stage CRN, using the paper's logical (history_t, A_t, Y_{t+1}).

    Frozen simulator-interface convention: values[:,j] = X_j includes Y_j;
    control_ctx[:,j] is the dose producing that observation, i.e. paper A_{j-1}.
    control_future[:,0] is the planned A_t producing the first target Y_{t+1}.
    Thus the encoder receives *previous* treatments, never the A_t classified
    by its own balanced representation. Simulator doses are indexed at their
    response endpoint, whereas paper doses are indexed at the decision time.

    The first decoder head predicts Y_{t+1} from its initialized state and A_t.
    The next recurrent update consumes (Y_{t+1}, A_t): observed Y for training,
    predicted Y for inference. No future target is read by default forward().
    """

    def __init__(self, n_obs=6, n_ctrl=1, d=96, representation_dim=96,
                 head_dim=96, lamb=1.0, dropout=0.1, treatment_bins=10,
                 legacy_zero=True):
        super().__init__()
        if (n_ctrl != 1 or min(n_obs, d, representation_dim, head_dim) < 1 or
                treatment_bins < 2 or lamb < 0 or not 0 <= dropout < 1):
            raise ValueError('Require one control, positive sizes and valid dropout/lambda')
        self.lamb = float(lamb)
        self.coefficient = 0.0
        self.config = dict(n_obs=n_obs, n_ctrl=n_ctrl, d=d,
                           representation_dim=representation_dim, head_dim=head_dim,
                           lamb=lamb, dropout=dropout, treatment_bins=treatment_bins,
                           legacy_zero=legacy_zero,
                           decoder_hidden_dim=representation_dim,
                           decoder_initial_hidden='encoder balanced representation directly',
                           decoder_initial_memory='zeros (paper does not specify cell memory)',
                           loss='mean trajectories of sum times of sum outcome coordinates',
                           treatment_adaptation='10 equal-width bins on [0,.5]' if treatment_bins == 10
                           else f'{treatment_bins} equal-width bins on [0,.5]')
        self.is_legacy = lamb == 0 and legacy_zero
        if self.is_legacy:
            from cvsim_counterfactual_runner import CRNLite
            self.legacy = CRNLite(n_obs=n_obs, n_ctrl=n_ctrl, d=d, lamb=0.0)
            return
        self.encoder = nn.LSTM(n_obs + n_ctrl, d, batch_first=True)
        self.encoder_representation = nn.Sequential(nn.Linear(d, representation_dim), nn.ELU())
        self.encoder_outcome = _head(representation_dim + n_ctrl, head_dim, n_obs)
        self.encoder_treatment = _head(representation_dim, head_dim, treatment_bins)
        # Appendix J: decoder RNN size equals encoder balanced-representation size.
        self.decoder = nn.LSTMCell(n_obs + n_ctrl, representation_dim)
        self.decoder_representation = nn.Sequential(
            nn.Linear(representation_dim, representation_dim), nn.ELU())
        self.decoder_outcome = _head(representation_dim + n_ctrl, head_dim, n_obs)
        self.decoder_treatment = _head(representation_dim, head_dim, treatment_bins)
        self.encoder_dropout = nn.Dropout(dropout)
        self.decoder_dropout = nn.Dropout(dropout)
        self.register_buffer('treatment_boundaries', torch.linspace(0., .5, treatment_bins + 1)[1:-1])
        self._balanced = None

    def set_epoch(self, epoch):
        self.coefficient = balancing_coefficient(epoch, self.lamb)

    def _encode(self, batch):
        # At index j: inputs X_j and paper A_{j-1}; output predicts Y_{j+1}.
        hidden, _ = self.encoder(torch.cat([batch['values'], batch['control_ctx']], -1))
        return self.encoder_dropout(self.encoder_representation(hidden))

    def treatment_labels(self, dose):
        if torch.any(~torch.isfinite(dose) | (dose < 0) | (dose > .5)):
            raise ValueError('CVSim treatment is outside the documented [0,.5] range')
        return torch.bucketize(dose.squeeze(-1).contiguous(), self.treatment_boundaries)

    def _balance(self, representation, dose, head):
        logits = head(grad_reverse(representation, self.coefficient))
        losses = F.cross_entropy(logits.reshape(-1, logits.shape[-1]),
                                 self.treatment_labels(dose).reshape(-1), reduction='none')
        # Appendix E uses the same trajectory/time aggregation for both terms.
        return losses.reshape(representation.shape[:2]).sum(1).mean()

    def encoder_loss(self, batch):
        """One-step triples: (X_j, previous A_{j-1}), current A_j, Y_{j+1}."""
        representation = self._encode(batch)
        if 'current_treatments' in batch:
            dose, target = batch['current_treatments'], batch['target']
        else:
            # Common fixed-window API, using endpoint-indexed simulator doses.
            dose = torch.cat([batch['control_ctx'][:, 1:], batch['control_future'][:, :1]], 1)
            target = torch.cat([batch['values'][:, 1:], batch['target'][:, :1]], 1)
        prediction = self.encoder_outcome(torch.cat([representation, dose], -1))
        outcome = trajectory_outcome_loss(prediction, target)
        balance = self._balance(representation, dose, self.encoder_treatment)
        return outcome + balance, outcome, balance

    def initial_decoder_state(self, encoder_representation):
        # Direct hidden initialization; no learned/tanh state projection.
        return encoder_representation, torch.zeros_like(encoder_representation)

    def rollout(self, batch, horizon, *, teacher_forcing=False):
        if self.is_legacy:
            if teacher_forcing:
                raise ValueError('Legacy CRN-lite has no teacher-forcing contract')
            return self.legacy.rollout(batch, horizon)
        if horizon < 1 or batch['control_future'].shape[1] < horizon:
            raise ValueError('Require positive horizon and a complete treatment plan')
        if teacher_forcing and ('target' not in batch or batch['target'].shape[1] < horizon):
            raise ValueError('Teacher forcing requires observed decoder targets')
        encoder_rep = (batch['initial_representation'] if 'initial_representation' in batch
                       else self._encode(batch)[:, -1])
        hidden, memory = self.initial_decoder_state(encoder_rep)
        predictions, representations = [], []
        for step in range(horizon):
            representation = self.decoder_dropout(self.decoder_representation(hidden))
            dose = batch['control_future'][:, step]
            prediction = self.decoder_outcome(torch.cat([representation, dose], -1))
            predictions.append(prediction)
            representations.append(representation)
            if step + 1 < horizon:
                previous_outcome = batch['target'][:, step] if teacher_forcing else prediction
                hidden, memory = self.decoder(torch.cat([previous_outcome, dose], -1),
                                              (hidden, memory))
        self._balanced = torch.stack(representations, 1)
        return torch.stack(predictions, 1)

    def aux_loss(self, batch):
        if self.is_legacy:
            return self.legacy.aux_loss(batch)
        if self._balanced is None:
            raise RuntimeError('Call rollout before aux_loss')
        return self._balance(self._balanced,
                             batch['control_future'][:, :self._balanced.shape[1]],
                             self.decoder_treatment)

    def forward(self, batch, horizon, *, teacher_forcing=False):
        return self.rollout(batch, horizon, teacher_forcing=teacher_forcing)

    def encoder_parameters(self):
        for module in (self.encoder, self.encoder_representation,
                       self.encoder_outcome, self.encoder_treatment):
            yield from module.parameters()

    def decoder_parameters(self):
        for module in (self.decoder, self.decoder_representation,
                       self.decoder_outcome, self.decoder_treatment):
            yield from module.parameters()


def factual_training_tensors(data, device):
    """Only factual training patients; preserve the frozen loader normalization."""
    index = data['tr']
    values = torch.as_tensor((data['obs'][index] - data['mean']) / data['std'], device=device)
    dose = torch.as_tensor(data['vaso'][index], device=device)
    return dict(values=values[:, :-1], control_ctx=dose[:, :-1],
                current_treatments=dose[:, 1:], target=values[:, 1:])


@torch.no_grad()
def decoder_training_tensors(model, encoder_batch, horizon):
    """Appendix E Eq. (19): every eligible trajectory split, initialized at br_l."""
    if not 1 <= horizon <= encoder_batch['target'].shape[1]:
        raise ValueError('Decoder horizon exceeds the factual trajectory')
    model.encoder.eval()
    model.encoder_representation.eval()
    model.encoder_dropout.eval()
    representations = model._encode(encoder_batch)
    splits = representations.shape[1] - horizon + 1
    # unfold places the window dimension last, so restore (patient,split,time,feature).
    outcomes = encoder_batch['target'].unfold(1, horizon, 1).permute(0, 1, 3, 2)
    doses = encoder_batch['current_treatments'].unfold(1, horizon, 1).permute(0, 1, 3, 2)
    return dict(initial_representation=representations[:, :splits].reshape(-1, representations.shape[-1]),
                control_future=doses.reshape(-1, horizon, doses.shape[-1]),
                target=outcomes.reshape(-1, horizon, outcomes.shape[-1]))


def train_crn(model, data, C, K, device='cpu', epochs=60, lr=.002, batch_size=128):
    """Encoder on all one-step factual transitions, frozen-encoder decoder on all splits.

    The total learned_graph_baselines budget remains split between stages (default 30/30 rather than
    paper 100/100). Decoder fitting explicitly teacher forces. Both loss terms
    sum times, outcome loss also sums coordinates, then average trajectories.
    lambda_max=1 retains the paper's unit trade-off on that scale, rather than
    compensating for learned_graph_baselines's former six-coordinate mean. Legacy stays frozen.
    """
    if model.is_legacy:
        from cvsim_counterfactual_runner import train
        if batch_size != 128:
            raise ValueError('Legacy regression uses the frozen batch size 128')
        train(model, data, C, K, torch.device(device), epochs, lr)
        return [dict(stage='legacy_crn_lite', epochs=epochs, lambda_max=0.)]
    if epochs < 2 or batch_size < 1:
        raise ValueError('Full CRN needs at least one epoch per stage and a positive batch')
    model.to(device)
    encoder_batch = factual_training_tensors(data, device)
    encoder_epochs = epochs // 2
    stages = (('encoder', encoder_epochs, list(model.encoder_parameters())),
              ('decoder', epochs - encoder_epochs, list(model.decoder_parameters())))
    history = []
    for stage, count, parameters in stages:
        tensors = encoder_batch
        if stage == 'decoder':
            for parameter in model.encoder_parameters():
                parameter.requires_grad_(False)
                parameter.grad = None
            tensors = decoder_training_tensors(model, encoder_batch, K)
        optimizer = torch.optim.Adam(parameters, lr=lr)
        n_examples = len(tensors['target'])
        for epoch in range(count):
            model.train()
            if stage == 'decoder':
                model.encoder.eval()
                model.encoder_representation.eval()
                model.encoder_dropout.eval()
            model.set_epoch(epoch + 1)
            order = torch.randperm(n_examples, device=device)
            totals = [0., 0., 0.]
            for start in range(0, n_examples, batch_size):
                selection = order[start:start + batch_size]
                batch = {name: value[selection] for name, value in tensors.items()}
                optimizer.zero_grad(set_to_none=True)
                if stage == 'encoder':
                    loss, outcome, balance = model.encoder_loss(batch)
                else:
                    prediction = model(batch, K, teacher_forcing=True)
                    outcome = trajectory_outcome_loss(prediction, batch['target'])
                    balance = model.aux_loss(batch)
                    loss = outcome + balance
                if not torch.isfinite(loss):
                    raise ValueError('Nonfinite CRN fitting loss')
                loss.backward()
                nn.utils.clip_grad_norm_(parameters, 1.)
                optimizer.step()
                for index, value in enumerate((loss, outcome, balance)):
                    totals[index] += float(value.detach()) * len(selection)
            record = dict(stage=stage, epoch=epoch, coefficient=model.coefficient,
                          loss=totals[0] / n_examples,
                          outcome_sse_per_trajectory=totals[1] / n_examples,
                          treatment_ce_sum_per_trajectory=totals[2] / n_examples,
                          n_examples=n_examples, teacher_forcing=stage == 'decoder')
            history.append(record)
            if epoch % 5 == 0 or epoch == count - 1:
                print(f'[crn_v2] {stage} epoch={epoch} '
                      f'outcome_sse={record["outcome_sse_per_trajectory"]:.6f} '
                      f'lambda={model.coefficient:.6f}', flush=True)
    return history
