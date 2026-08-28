"""cvsim_hemodynamics_simulator — closed-loop mean-circulation cardiovascular model.

A four-compartment (systemic arterial / systemic venous / pulmonary arterial /
pulmonary venous) closed-loop circulation with two Frank-Starling ventricles, an
arterial baroreflex, and a sepsis-like disease axis. Parameter scales follow the
CVSim lumped-parameter tradition (Heldt et al., MIT-LCP/cvsim); this is a
mean-field reduction intended for *trajectory-level* counterfactuals at ICU time
resolution rather than beat-resolved waveforms.

It is the counterfactual GROUND TRUTH for PhysioGraph: because the generative
model is known, the true response to an alternative treatment (a different
vasopressor dose, a fluid bolus) is computable, which observational ICU data can
never provide. Used by stage 2 to emit factual + counterfactual trajectories.

Self-test (``python cvsim_hemodynamics_simulator.py``) auto-calibrates the
baseline and checks that a vasopressor raises MAP and a fluid bolus raises CVP.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

# Units: pressure mmHg, volume mL, flow mL/s, resistance mmHg*s/mL,
# compliance mL/mmHg, time s, heart rate beats/min.

MMHG_PER_S_TO_PER_MIN = 60.0


@dataclass
class Hemodynamics:
    """Nominal adult parameters; per-patient values are sampled around these."""
    # Compliances (mL/mmHg)
    C_sa: float = 1.6
    C_sv: float = 100.0
    C_pa: float = 4.3
    C_pv: float = 10.0
    # Unstressed volumes (mL)
    V0_sa: float = 100.0
    V0_sv: float = 2900.0
    V0_pa: float = 50.0
    V0_pv: float = 150.0
    # Resistances (mmHg*s/mL)
    R_sys: float = 1.0       # total peripheral resistance (baroreflex / vasopressor target)
    R_pul: float = 0.12
    # Heart: saturating Frank-Starling, SV = SVmax * P_fill/(P_fill+k) * contractility
    SVmax_l: float = 105.0
    SVmax_r: float = 105.0
    k_l: float = 6.0         # mmHg, LV filling half-saturation (preload = P_pv)
    k_r: float = 3.0         # mmHg, RV filling half-saturation (preload = P_sv)
    cont_l: float = 1.0
    cont_r: float = 1.0
    HR: float = 70.0         # beats/min
    # Total blood volume (mL); calibrated so baseline MAP ~ target
    V_total: float = 5000.0
    # Renal: urine output (mL/min) as a saturating function of mean arterial pressure
    UO_max: float = 1.6
    MAP_renal: float = 65.0
    uo_scale: float = 8.0
    # Metabolic: lactate (mmol/L) dynamics driven by hypoperfusion + sepsis
    lac_base: float = 1.0
    k_lac_prod: float = 0.0011
    k_lac_clear: float = 0.0003
    MAP_lac_crit: float = 65.0
    lac_scale: float = 10.0
    # cross-organ coupling strength (H3): 0 -> organs ~independent; 1 -> strong nonlinear coupling
    complexity: float = 1.0
    # Baroreflex
    MAP_set: float = 90.0
    tau_baro: float = 12.0   # s, effector time constant
    g_hr: float = 0.55       # beats/min per mmHg error
    g_r: float = 0.018       # fractional R_sys change per mmHg error
    g_cont: float = 0.010    # fractional contractility change per mmHg error
    g_ven: float = 9.0       # mL unstressed-volume shift per mmHg error (venous tone)
    baro_on: bool = True


# ----------------------------------------------------------------------------
# Intervention schedule
# ----------------------------------------------------------------------------
@dataclass
class InterventionSchedule:
    """Time-varying treatment controls, all in clinically interpretable units.

    vaso_dose: norepinephrine-equivalent (mcg/kg/min), piecewise-constant.
    fluid_rate: crystalloid infusion (mL/s), piecewise-constant.
    sepsis: disease severity in [0,1] (vasodilation + capillary leak + cardiodepression).
    Each is given as (times[s], values) breakpoints, held constant between knots.
    """
    horizon_s: float = 6 * 3600.0
    vaso_t: np.ndarray = field(default_factory=lambda: np.array([0.0]))
    vaso_v: np.ndarray = field(default_factory=lambda: np.array([0.0]))
    fluid_t: np.ndarray = field(default_factory=lambda: np.array([0.0]))
    fluid_v: np.ndarray = field(default_factory=lambda: np.array([0.0]))
    sepsis_t: np.ndarray = field(default_factory=lambda: np.array([0.0]))
    sepsis_v: np.ndarray = field(default_factory=lambda: np.array([0.0]))

    @staticmethod
    def _step(t, knots_t, knots_v):
        idx = np.searchsorted(knots_t, t, side="right") - 1
        return knots_v[max(0, idx)]

    def vaso(self, t):    return self._step(t, self.vaso_t, self.vaso_v)
    def fluid(self, t):   return self._step(t, self.fluid_t, self.fluid_v)
    def sepsis(self, t):  return self._step(t, self.sepsis_t, self.sepsis_v)


# Pharmacodynamic / disease gains
G_VASO_R = 0.95     # vasopressor -> fractional TPR increase per (mcg/kg/min)
G_VASO_CONT = 0.30  # vasopressor -> fractional contractility increase
G_VASO_VEN = 180.0  # vasopressor -> venoconstriction (mL unstressed shift)
G_SEP_R = 0.55      # sepsis -> fractional TPR decrease
G_SEP_LEAK = 0.10   # sepsis -> capillary leak (mL/s at severity 1)
G_SEP_CONT = 0.35   # sepsis -> fractional contractility decrease


class CVSim:
    """Closed-loop mean-circulation simulator with baroreflex + interventions."""

    STATE = ("V_sa", "V_sv", "V_pa", "V_pv", "e_hr", "e_r", "e_cont", "e_ven")

    def __init__(self, p: Hemodynamics):
        self.p = p

    # --- pressures from volumes ---
    def _pressures(self, V_sa, V_sv, V_pa, V_pv, e_ven):
        p = self.p
        P_sa = (V_sa - p.V0_sa) / p.C_sa
        P_sv = (V_sv - (p.V0_sv - e_ven)) / p.C_sv   # venous tone shifts unstressed vol
        P_pa = (V_pa - p.V0_pa) / p.C_pa
        P_pv = (V_pv - p.V0_pv) / p.C_pv
        return P_sa, P_sv, P_pa, P_pv

    def _rhs(self, t, y, sch: InterventionSchedule):
        p = self.p
        V_sa, V_sv, V_pa, V_pv, e_hr, e_r, e_cont, e_ven, Lac = y
        vaso, fluid, sep = sch.vaso(t), sch.fluid(t), sch.sepsis(t)

        P_sa, P_sv, P_pa, P_pv = self._pressures(V_sa, V_sv, V_pa, V_pv, e_ven)
        P_pv_eff = max(P_pv, 0.0)
        P_sv_eff = max(P_sv, 0.0)

        # effective parameters after interventions + disease + reflex effectors
        R_sys = p.R_sys * (1.0 + G_VASO_R * vaso) * (1.0 - G_SEP_R * sep) * (1.0 + e_r)
        R_sys = max(R_sys, 0.05)
        cont_l = p.cont_l * (1.0 + G_VASO_CONT * vaso) * (1.0 - G_SEP_CONT * sep) * (1.0 + e_cont)
        cont_r = p.cont_r * (1.0 + G_VASO_CONT * vaso) * (1.0 - G_SEP_CONT * sep) * (1.0 + e_cont)
        HR = np.clip(p.HR + e_hr, 35.0, 180.0)
        hr_hz = HR / 60.0

        # Frank-Starling stroke volumes -> cardiac outputs (mL/s)
        SV_l = p.SVmax_l * P_pv_eff / (P_pv_eff + p.k_l) * cont_l
        SV_r = p.SVmax_r * P_sv_eff / (P_sv_eff + p.k_r) * cont_r
        CO_l = hr_hz * SV_l
        CO_r = hr_hz * SV_r

        Q_sys = (P_sa - P_sv) / R_sys
        Q_pul = (P_pa - P_pv) / p.R_pul
        leak = G_SEP_LEAK * sep      # capillary leak removes circulating volume

        dV_sa = CO_l - Q_sys
        dV_sv = Q_sys - CO_r + fluid - leak
        dV_pa = CO_r - Q_pul
        dV_pv = Q_pul - CO_l

        # baroreflex effectors relax toward target driven by MAP error
        if p.baro_on:
            err = p.MAP_set - P_sa
            de_hr = (p.g_hr * err - e_hr) / p.tau_baro
            de_r = (p.g_r * err - e_r) / p.tau_baro
            de_cont = (p.g_cont * err - e_cont) / p.tau_baro
            de_ven = (p.g_ven * err - e_ven) / p.tau_baro
        else:
            de_hr = de_r = de_cont = de_ven = 0.0

        # metabolic: lactate rises with hypoperfusion (low MAP) and sepsis, clears first-order.
        # The cardio->metabolic coupling (via hypoperf) is scaled by complexity (H3).
        hypoperf = 1.0 / (1.0 + np.exp((P_sa - p.MAP_lac_crit) / p.lac_scale))
        dLac = p.k_lac_prod * (sep + p.complexity * 1.5 * hypoperf) - p.k_lac_clear * Lac

        return np.array([dV_sa, dV_sv, dV_pa, dV_pv, de_hr, de_r, de_cont, de_ven, dLac])

    def initial_state(self):
        """Distribute total blood volume across compartments at unstressed + share."""
        p = self.p
        unstressed = p.V0_sa + p.V0_sv + p.V0_pa + p.V0_pv
        stressed = max(p.V_total - unstressed, 200.0)
        # split stressed volume by compliance (charge to similar pressure)
        Csum = p.C_sa + p.C_sv + p.C_pa + p.C_pv
        V_sa = p.V0_sa + stressed * p.C_sa / Csum
        V_sv = p.V0_sv + stressed * p.C_sv / Csum
        V_pa = p.V0_pa + stressed * p.C_pa / Csum
        V_pv = p.V0_pv + stressed * p.C_pv / Csum
        return np.array([V_sa, V_sv, V_pa, V_pv, 0.0, 0.0, 0.0, 0.0, p.lac_base])

    def simulate(self, sch: InterventionSchedule, dt=0.05, out_dt=60.0, y0=None,
                 warmup_s=120.0):
        """Integrate (RK4) and return observables sampled every ``out_dt`` seconds.

        Returns dict of arrays: t(min), MAP, HR, CO(L/min), CVP, SV(mL), Ppv, sepsis,
        vaso, fluid. A warmup brings the system to its (possibly diseased) baseline
        before t=0 observables begin.
        """
        y = self.initial_state() if y0 is None else y0.copy()
        # warmup at the t=0 controls to settle transients
        warm = InterventionSchedule(
            horizon_s=warmup_s,
            vaso_v=np.array([sch.vaso(0.0)]), fluid_v=np.array([0.0]),
            sepsis_v=np.array([sch.sepsis(0.0)]))
        n_warm = int(warmup_s / dt)
        for i in range(n_warm):
            y = self._rk4(i * dt, y, warm, dt)

        n = int(sch.horizon_s / dt)
        stride = max(1, int(round(out_dt / dt)))
        rec = []
        for i in range(n + 1):
            t = i * dt
            if i % stride == 0:
                rec.append(self._observe(t, y, sch))
            if i < n:
                y = self._rk4(t, y, sch, dt)
        R = np.array(rec)
        keys = ("t_min", "MAP", "HR", "CO", "CVP", "UO", "Lac", "sepsis", "vaso")
        return {k: R[:, j] for j, k in enumerate(keys)}

    def _rk4(self, t, y, sch, dt):
        k1 = self._rhs(t, y, sch)
        k2 = self._rhs(t + dt / 2, y + dt / 2 * k1, sch)
        k3 = self._rhs(t + dt / 2, y + dt / 2 * k2, sch)
        k4 = self._rhs(t + dt, y + dt * k3, sch)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        # volumes stay non-negative; lactate stays >= floor
        y[:4] = np.maximum(y[:4], 1.0)
        y[8] = max(y[8], 0.05)
        return y

    def _observe(self, t, y, sch):
        p = self.p
        V_sa, V_sv, V_pa, V_pv, e_hr, e_r, e_cont, e_ven, Lac = y
        P_sa, P_sv, P_pa, P_pv = self._pressures(V_sa, V_sv, V_pa, V_pv, e_ven)
        vaso, sep = sch.vaso(t), sch.sepsis(t)
        cont_l = p.cont_l * (1 + G_VASO_CONT * vaso) * (1 - G_SEP_CONT * sep) * (1 + e_cont)
        HR = float(np.clip(p.HR + e_hr, 35.0, 180.0))
        SV_l = p.SVmax_l * max(P_pv, 0) / (max(P_pv, 0) + p.k_l) * cont_l
        CO = HR / 60.0 * SV_l * MMHG_PER_S_TO_PER_MIN / 1000.0  # L/min
        # renal: urine output couples to MAP with strength scaled by complexity (H3);
        # at complexity 0 it is ~constant (organ independent), at 1 it tracks MAP.
        uo_full = 1.0 / (1.0 + np.exp(-(P_sa - p.MAP_renal) / p.uo_scale))
        UO = p.UO_max * ((1.0 - p.complexity) * 0.7 + p.complexity * uo_full)  # mL/min, renal
        return (t / 60.0, P_sa, HR, CO, P_sv, UO, Lac, sep, vaso)

    # --- calibration ---
    def calibrate_volume(self, target_map=90.0, lo=3800.0, hi=6500.0, iters=28):
        """Bisection on V_total so the healthy steady-state MAP hits target."""
        base = InterventionSchedule(horizon_s=400.0)
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            self.p = replace(self.p, V_total=mid)
            out = self.simulate(base, dt=0.05, out_dt=50.0, warmup_s=400.0)
            if out["MAP"][-1] < target_map:
                lo = mid
            else:
                hi = mid
        self.p = replace(self.p, V_total=0.5 * (lo + hi))
        return self.p.V_total


# ----------------------------------------------------------------------------
# Patient sampling + counterfactual dataset
# ----------------------------------------------------------------------------
def sample_patient(rng: np.random.Generator, complexity=1.0) -> Hemodynamics:
    """Heterogeneous patient: varied baseline tone, contractility, reflex gain."""
    p = Hemodynamics(
        complexity=complexity,
        R_sys=float(rng.uniform(0.80, 1.30)),
        SVmax_l=float(rng.uniform(90, 120)),
        SVmax_r=float(rng.uniform(90, 120)),
        cont_l=float(rng.uniform(0.80, 1.15)),
        cont_r=float(rng.uniform(0.80, 1.15)),
        HR=float(rng.uniform(60, 85)),
        MAP_set=float(rng.uniform(85, 95)),
        g_hr=float(rng.uniform(0.4, 0.7)),
        C_sa=float(rng.uniform(1.3, 1.9)),
        V_total=float(rng.uniform(4200, 5200)),  # baroreflex self-regulates baseline MAP
    )
    return p


def _sepsis_onset_schedule(rng, horizon_s, sev):
    """A sepsis severity ramp starting at a random early time."""
    onset = rng.uniform(0.0, horizon_s * 0.25)
    t = np.array([0.0, onset, onset + 1800.0, horizon_s])
    v = np.array([0.0, 0.0, sev, sev])
    return t, v


def make_counterfactual_dataset(n_patients=400, horizon_h=6.0, out_dt=300.0,
                                seed=0, out_path=None, confound=1.0, coupling=1.0):
    """Emit factual + counterfactual trajectories under alternative vasopressor doses.

    For each patient we fix a sepsis course and a *factual* clinician policy
    (a vasopressor dose chosen with confounding-by-severity: sicker patients get
    more drug). We then roll out the SAME patient under a grid of counterfactual
    constant doses. Because the generator is known, these are true counterfactuals.
    """
    rng = np.random.default_rng(seed)
    horizon_s = horizon_h * 3600.0
    cf_doses = np.array([0.0, 0.05, 0.10, 0.20, 0.40])  # mcg/kg/min
    data = {"patient": [], "severity": [], "factual_dose": [],
            "t_min": None, "factual": [], "cf_doses": cf_doses, "counterfactual": []}

    for i in range(n_patients):
        p = sample_patient(rng, complexity=coupling)
        sim = CVSim(p)
        sev = float(rng.uniform(0.2, 0.9))
        st, sv = _sepsis_onset_schedule(rng, horizon_s, sev)
        y0 = sim.initial_state()

        # factual policy: confound in [0,1] interpolates between random dosing (full
        # overlap) and severity-driven dosing (low overlap / strong confounding).
        random_dose = rng.uniform(0.0, 0.5)
        fdose = float(np.clip(confound * (0.5 * sev) + (1 - confound) * random_dose
                              + rng.normal(0, 0.03), 0.0, 0.5))
        f_t = np.array([0.0, horizon_s * 0.2, horizon_s])
        f_v = np.array([0.0, fdose, fdose])
        f_sched = InterventionSchedule(horizon_s, f_t, f_v,
                                       sepsis_t=st, sepsis_v=sv)
        fout = sim.simulate(f_sched, dt=0.5, out_dt=out_dt, y0=y0, warmup_s=180.0)

        cf_traj = []
        for d in cf_doses:
            cf_sched = InterventionSchedule(
                horizon_s, np.array([0.0]), np.array([d]),
                sepsis_t=st, sepsis_v=sv)
            cf = sim.simulate(cf_sched, dt=0.5, out_dt=out_dt, y0=y0, warmup_s=180.0)
            cf_traj.append(np.stack(
                [cf["MAP"], cf["HR"], cf["CO"], cf["CVP"], cf["UO"], cf["Lac"]], -1))

        data["patient"].append(i)
        data["severity"].append(sev)
        data["factual_dose"].append(fdose)
        data["t_min"] = fout["t_min"]
        data["factual"].append(np.stack(
            [fout["MAP"], fout["HR"], fout["CO"], fout["CVP"], fout["UO"], fout["Lac"],
             fout["vaso"], fout["sepsis"]], -1))
        data["counterfactual"].append(np.stack(cf_traj, 0))

    packed = {
        "t_min": data["t_min"].astype(np.float32),
        "cf_doses": cf_doses.astype(np.float32),
        "severity": np.array(data["severity"], np.float32),
        "factual_dose": np.array(data["factual_dose"], np.float32),
        "factual": np.array(data["factual"], np.float32),          # (N,T,8): 6 obs+vaso+sepsis
        "counterfactual": np.array(data["counterfactual"], np.float32),  # (N,D,T,6)
        "channels": np.array(["MAP", "HR", "CO", "CVP", "UO", "Lac"]),
    }
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, **packed)
    return packed


def _selftest():
    print("[cvsim] calibrating baseline ...")
    sim = CVSim(Hemodynamics())
    V = sim.calibrate_volume(target_map=90.0)
    base = sim.simulate(InterventionSchedule(horizon_s=600.0), out_dt=60.0)
    print(f"  V_total={V:6.0f} mL | baseline MAP={base['MAP'][-1]:5.1f} "
          f"HR={base['HR'][-1]:4.1f} CO={base['CO'][-1]:4.2f} L/min CVP={base['CVP'][-1]:4.1f}")
    assert 80 < base["MAP"][-1] < 100, "baseline MAP off"
    assert 3.5 < base["CO"][-1] < 7.5, "baseline CO off"

    # vasopressor must raise MAP
    sch = InterventionSchedule(horizon_s=1800.0,
                               vaso_t=np.array([0.0, 600.0]), vaso_v=np.array([0.0, 0.25]))
    out = sim.simulate(sch, out_dt=60.0)
    map_pre = out["MAP"][9]; map_post = out["MAP"][-1]
    print(f"  vasopressor 0.25: MAP {map_pre:.1f} -> {map_post:.1f}")
    assert map_post > map_pre + 3, "vasopressor did not raise MAP"

    # fluid bolus must raise CVP
    sch2 = InterventionSchedule(horizon_s=1800.0,
                                fluid_t=np.array([0.0, 600.0, 900.0]),
                                fluid_v=np.array([0.0, 2.0, 0.0]))  # ~500mL over 5min
    out2 = sim.simulate(sch2, out_dt=60.0)
    print(f"  fluid bolus: CVP {out2['CVP'][9]:.1f} -> {out2['CVP'][16]:.1f}")
    assert out2["CVP"][16] > out2["CVP"][9] + 0.5, "fluid did not raise CVP"
    print("[cvsim] self-test PASSED")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--gen", type=str, default="", help="output npz path for dataset")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--confound", type=float, default=1.0)
    ap.add_argument("--coupling", type=float, default=1.0)
    args = ap.parse_args()
    if args.gen:
        d = make_counterfactual_dataset(n_patients=args.n, seed=args.seed, out_path=args.gen,
                                        confound=args.confound, coupling=args.coupling)
        print(f"[cvsim] wrote {args.gen}: factual{d['factual'].shape} "
              f"counterfactual{d['counterfactual'].shape}")
    else:
        _selftest()
