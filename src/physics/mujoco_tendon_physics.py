"""
MuJoCo Physics Engine with Tendon-Based Actuation

Actuation mechanism
-------------------
- Every adjacent voxel pair has a spatial tendon + position actuator
- force = kp * (ctrl - current_length)   [per-tendon kp from material types]
- Active tendons:   ctrl = rest * (1 + amplitude * signal)
    - Without controller: signal = sin(omega*t + base_phase)
    - With CPGController:  signal = cpg.step(dt)[active_tendon_index]
- Passive tendons:  ctrl = rest  (holds shape)

Settled measurement
-------------------
get_fitness() runs 0.5 s of actuation before recording start position,
so initial-contact noise is excluded from the locomotion score.
"""
import numpy as np
import mujoco
from typing import Optional, List, Dict
from src.physics.mujoco_tendon_converter import voxel_to_tendon_xml


class MuJoCoTendonPhysics:
    """Tendon-based soft robot physics engine."""

    def __init__(
        self,
        default_timestep: float = 0.0005,
        actuation_frequency: float = 10.0,
        actuation_amplitude: float = 0.20,
        fitness_mode: str = "directed",
        max_voxels: Optional[int] = None,
        friction: Optional[Dict] = None,
        direction: str = "forward",
        divide_by: str = "body",
        workspace_voxels: Optional[int] = None,
    ):
        """friction: None keeps the original floor (dynamic contact, coefficient 0.7).
            {'mode': 'single', 'mu': MU} -> one sliding coefficient for voxel-floor contact.
            {'mode': 'stickslip', 'mu_s': MS, 'mu_k': MK, 'v_on': V1, 'v_off': V0} ->
            Voxelyze-style static/kinetic friction: each voxel is either stuck (floor
            friction MS) or sliding (MK). It starts sliding once its horizontal speed
            exceeds V1 and sticks again below V0 (m/s; hysteresis stops flicker at the
            threshold). Voxelyze switches on lateral force > MS x normal force, but MuJoCo
            only reveals contact forces after its solve, so speed is the trigger here.
            Either way voxel-voxel contacts are untouched.

        direction / divide_by: what distance the score counts and what it is divided by.
            direction 'forward' (default): the +X component of the COM displacement.
            direction 'any': the length of the 3D COM displacement in any direction - Cheney
                2013's Voxelyze FinalCOM_Dist = (GetCM() - IniCM).Length().
            divide_by 'body' (default): the body's own longest side -> body lengths (BL).
            divide_by 'workspace': a FIXED width of `workspace_voxels` voxels, as Cheney 2013
                (fitness = |dCOM| / (BoundingBoxLength x VoxelSize)). Every body is then scored
                in the same unit, so a body shorter than the workspace gets no workspace/length
                bonus. The early-termination threshold is in the same unit and direction."""
        if direction not in ("forward", "any"):
            raise ValueError(f"direction must be 'forward' or 'any', got {direction!r}")
        if divide_by not in ("body", "workspace"):
            raise ValueError(f"divide_by must be 'body' or 'workspace', got {divide_by!r}")
        if divide_by == "workspace" and not (workspace_voxels and int(workspace_voxels) > 0):
            raise ValueError("divide_by='workspace' needs workspace_voxels (the grid side, > 0)")
        self.direction           = direction
        self.divide_by           = divide_by
        self.workspace_voxels    = None if workspace_voxels is None else int(workspace_voxels)
        self.default_timestep    = default_timestep
        self.actuation_frequency = actuation_frequency
        self.actuation_amplitude = actuation_amplitude
        self.fitness_mode        = fitness_mode   # directed|forward|efficiency|stable|skip|skipbl|musclecost
        self.voxel_size          = 0.01   # set per-robot in load_robot; used for body-length norm
        # Voxel budget, needed to normalise the muscle-cost penalty the way Cheney 2013 does
        # (penalty = metric / maximum possible metric). Threaded from the CLI --max-voxels,
        # because worker processes re-import genome_config defaults and can't see the parent's.
        self.max_voxels          = max_voxels
        self._n_actuated_voxels  = 0      # muscle voxels (materials 1,2) in the loaded body
        self._n_voxels           = 0
        self.friction            = friction
        self._ss_vidx            = None   # stick-slip: (n_voxels, 2) qvel indices of vx, vy
        self._ss_sliding         = None   # stick-slip: per-voxel state (True = sliding)

        self.model: Optional[mujoco.MjModel] = None
        self.data:  Optional[mujoco.MjData]  = None
        self.current_time = 0.0

        # Populated by load_robot()
        self.tendon_info:   List[Dict]           = []
        self.rest_lengths:  Optional[np.ndarray] = None

        # Precomputed arrays (set in _precompute_actuation_arrays)
        self._active_mask:  Optional[np.ndarray] = None   # bool (n_tendons,)
        self._base_phases:  Optional[np.ndarray] = None   # float (n_tendons,)
        self._active_idx:   Optional[np.ndarray] = None   # int indices of active tendons

        # Optional CPGController (set via set_controller())
        self._controller = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_robot(
        self,
        voxel_grid: np.ndarray,
        voxel_size: float = 0.01,
        initial_height: float = 0.0,
        gait_params=None,   # gait provider: (kx,ky,kz,offset) wave tuple, a control CPPN
                            # (per-voxel phase, detected by .evaluate_batch), or None
    ) -> None:
        """Load robot from voxel grid, record rest lengths, precompute arrays."""
        self.voxel_size = voxel_size
        # Material census for the muscle-cost fitness mode (1,2 = muscle; 3 soft, 4 stiff).
        self._n_voxels          = int((voxel_grid != 0).sum())
        self._n_actuated_voxels = int(((voxel_grid == 1) | (voxel_grid == 2)).sum())
        fr = self.friction
        floor_mu = None if fr is None else (fr['mu'] if fr['mode'] == 'single' else fr['mu_s'])
        xml, self.tendon_info = voxel_to_tendon_xml(voxel_grid, voxel_size, initial_height,
                                                    floor_friction=floor_mu)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data  = mujoco.MjData(self.model)
        self._ss_vidx = self._ss_sliding = None
        if fr is not None and fr['mode'] == 'stickslip':
            # voxel k <-> free joint k <-> floor pair k; free-joint qvel[0:3] is the
            # world-frame linear velocity. Every voxel starts stuck (static friction).
            adr = self.model.jnt_dofadr[:self.model.npair]
            self._ss_vidx    = np.stack([adr, adr + 1], axis=1)
            self._ss_sliding = np.zeros(self.model.npair, dtype=bool)
        mujoco.mj_forward(self.model, self.data)
        # Only active tendons have position actuators; rest_lengths tracks those.
        self.rest_lengths = np.array(self.data.actuator_length, copy=True)
        self.current_time = 0.0
        self._controller  = None
        self._precompute_actuation_arrays()
        if gait_params is not None:
            # A control CPPN (per-voxel evolvable phase) exposes evaluate_batch; a
            # 4-tuple is the legacy global traveling wave. Dispatch on that.
            if hasattr(gait_params, 'evaluate_batch'):
                self._apply_phase_cppn(gait_params)
            else:
                self._apply_gait_params(gait_params)

    def _apply_phase_cppn(self, phase_cppn) -> None:
        """Per-voxel evolvable phase: a co-evolving control CPPN maps each active tendon's
        normalised midpoint (x,y,z,dist) -> an actuation phase, replacing the 4-gene global
        wave with an arbitrary spatial phase field. The CPPN's first output (tanh, in
        [-1,1]) is scaled to a phase in [-pi, pi]. This is a strict generalisation of the
        plane wave, giving evolution spatially-rich control the single-blob body lacked."""
        active = [info for info in self.tendon_info if info['is_active']]
        if not active or self._base_phases is None:
            return
        xp  = self.data.xpos                       # voxel i -> body i+1 (world is body 0)
        pos = np.array([0.5 * (xp[1 + info['body1_idx']] + xp[1 + info['body2_idx']])
                        for info in active])
        span = pos.max(0) - pos.min(0)
        span = np.where(span < 1e-6, 1.0, span)
        n    = 2.0 * (pos - pos.min(0)) / span - 1.0            # per-axis -> [-1, 1]
        dn   = np.sqrt((n ** 2).sum(1)) / np.sqrt(3.0)
        coords = np.column_stack([n, dn]).astype(np.float32)    # (n_active, 4)
        raw  = phase_cppn.evaluate_batch(coords)[:, 0]          # first output, tanh [-1,1]
        gain = getattr(phase_cppn, 'phase_gain', None)          # None = full range (original)
        self._base_phases = ((1.0 if gain is None else float(gain)) * np.pi * raw).astype(float)

    def _apply_gait_params(self, gait_params) -> None:
        """C6: override the material-derived base phases with an evolved spatial
        traveling wave  phase(x,y,z) = 2π(kx·xn + ky·yn + kz·zn) + offset, evaluated at
        each active tendon's midpoint (normalised over the body's bounding box). Lets the
        gait co-evolve with the body in the tendon engine (ceiling ~1.08 BL)."""
        active = [info for info in self.tendon_info if info['is_active']]
        if not active or self._base_phases is None:
            return
        xp  = self.data.xpos                       # voxel i -> body i+1 (world is body 0)
        pos = np.array([0.5 * (xp[1 + info['body1_idx']] + xp[1 + info['body2_idx']])
                        for info in active])
        span = pos.max(0) - pos.min(0)
        span = np.where(span < 1e-6, 1.0, span)
        n    = (pos - pos.min(0)) / span
        kx, ky, kz, offset = gait_params
        self._base_phases = (2.0 * np.pi * (kx * n[:, 0] + ky * n[:, 1] + kz * n[:, 2])
                             + offset).astype(float)

    def _precompute_actuation_arrays(self) -> None:
        """Build base-phase array for the open-loop sinusoidal fallback.

        After the passive-spring optimisation, model.nu == num_active_tendons,
        so _base_phases is indexed 0..nu-1 and no active-mask indexing is needed.
        """
        self._base_phases = np.array(
            [info['base_phase'] for info in self.tendon_info if info['is_active']],
            dtype=float,
        )
        # Keep _active_mask/_active_idx as None — no longer used.
        self._active_mask = None
        self._active_idx  = None

    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------
    def set_controller(self, controller) -> None:
        """
        Attach a CPGController (or None to remove it).
        The controller must have num_actuators == number of active tendons.
        """
        if controller is not None:
            if controller.num_actuators != self.num_active_tendons:
                raise ValueError(
                    f"Controller has {controller.num_actuators} actuators but "
                    f"robot has {self.num_active_tendons} active tendons."
                )
        self._controller = controller

    def _actuator_count(self) -> int:
        """How many things drive this body; 0 means it cannot locomote (get_fitness scores 0).
        Here: position actuators on active tendons. Subclasses without MuJoCo actuators override."""
        return int(self.model.nu)

    @property
    def num_active_tendons(self) -> int:
        """Number of position-actuated (active) tendons == model.nu."""
        if self.model is None:
            return 0
        return int(self.model.nu)

    # ------------------------------------------------------------------
    # Actuation (vectorised — no Python loop per step)
    # ------------------------------------------------------------------
    def apply_actuation(self) -> None:
        """Set ctrl for every active-tendon actuator. O(n) numpy, no Python loop.

        model.nu == num_active_tendons after the passive-spring optimisation,
        so data.ctrl and rest_lengths are both indexed 0..nu-1 with no masking.
        """
        if self.rest_lengths is None or self.model.nu == 0:
            return

        if self._controller is not None:
            signals = self._controller.step(self.default_timestep)   # (nu,)
            signals = np.clip(signals, -1.0, 1.0)
            self.data.ctrl[:] = self.rest_lengths * (1.0 + self.actuation_amplitude * signals)
        else:
            omega = 2.0 * np.pi * self.actuation_frequency
            t_sig = self.actuation_amplitude * np.sin(
                omega * self.current_time + self._base_phases
            )
            self.data.ctrl[:] = self.rest_lengths * (1.0 + t_sig)

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------
    def step(self) -> None:
        """Advance simulation by one timestep."""
        if self.model is None:
            return
        self.apply_actuation()
        if self._ss_sliding is not None:
            self._update_floor_friction()
        mujoco.mj_step(self.model, self.data)
        self.current_time += self.default_timestep

    def _update_floor_friction(self) -> None:
        """Stick-slip: switch each voxel between static and kinetic floor friction from its
        current horizontal speed (hysteresis v_off < v_on). Vectorised, O(n_voxels)."""
        v     = self.data.qvel[self._ss_vidx]
        speed = np.hypot(v[:, 0], v[:, 1])
        fr    = self.friction
        self._ss_sliding = np.where(self._ss_sliding, speed > fr['v_off'], speed > fr['v_on'])
        mu = np.where(self._ss_sliding, fr['mu_k'], fr['mu_s'])
        self.model.pair_friction[:, 0] = mu
        self.model.pair_friction[:, 1] = mu

    # ------------------------------------------------------------------
    # Position / fitness
    # ------------------------------------------------------------------
    def get_position(self) -> np.ndarray:
        """Centre-of-mass of all voxel bodies (excludes worldbody at index 0)."""
        if self.data is None:
            return np.zeros(3)
        return np.mean(self.data.xpos[1:self.model.nbody], axis=0)

    def get_fitness(
        self,
        simulation_time:      float = 5.0,
        settle_time:          float = 0.5,
        early_term_fraction:  float = 0.2,
        early_term_threshold: float = 0.05,   # progress in score units (see direction/divide_by)
        return_descriptors:   bool  = False,  # also return (mean COM height, bounce) for MAP-Elites
    ):
        """
        Run simulation and return FORWARD (+X) distance in BODY LENGTHS, penalised
        by ground_fraction:

            fitness = max(0, forward_displacement / body_length) * ground_fraction

        - **Directed** (+X only): spinning, drift and backward motion score 0, so the
          objective selects for real forward locomotion (more transferable than the
          old undirected net-displacement metric).
        - **Body-length normalised**: comparable across body sizes.
          body_length = largest bounding-box extent of the undeformed body + one voxel.
          (Defaults. `direction='any'` / `divide_by='workspace'` switch to Cheney 2013's
          undirected 3D distance over a fixed workspace width - see __init__.)
        - **ground_fraction**: fraction of measurement steps the COM stays below 2× its
          *robust resting height* — the median COM-z over the final quarter of settling,
          so a mid-settle bounce no longer inflates the threshold (the old
          `initial_pos[2]*3.0` bug that quietly rewarded jumping).
        - **skip** mode softens this cliff into a ramp: full credit ≤2× resting, linearly
          decaying to 0 at 3.5× resting, so moderate skipping keeps most of its credit while
          sustained ballistic flight (jumping) still earns nothing.

        Early termination: at `early_term_fraction` of the window, if forward progress
        is below `early_term_threshold` body-lengths the robot is judged non-locomoting
        and the sim aborts with the partial result (short-circuits the non-movers /
        backward-movers that dominate any population).

        NOTE: this is a NEW metric (forward body-lengths) — values are NOT comparable to
        the earlier metres-based runs (0.116–0.1837 m).
        """
        nbody = self.model.nbody

        # Body length from the undeformed layout (positions before any stepping).
        init_xpos   = np.array(self.data.xpos[1:nbody], copy=True)
        extents     = init_xpos.max(axis=0) - init_xpos.min(axis=0)
        body_length = max(float(extents.max()) + self.voxel_size, self.voxel_size)

        # Settle, recording resting COM-z over the final quarter (robust to bounce).
        settle_steps = int(settle_time / self.default_timestep)
        track_from   = int(settle_steps * 0.75)
        heights      = []
        for s in range(settle_steps):
            self.step()
            if s >= track_from:
                heights.append(float(np.mean(self.data.xpos[1:nbody, 2])))
        settled_height   = float(np.median(heights)) if heights \
            else float(np.mean(self.data.xpos[1:nbody, 2]))
        ground_threshold = max(settled_height * 2.0, 0.05)

        # --fitness skip: graded ground credit. Full credit while the COM stays below the
        # 2x-resting threshold; a "skip" that briefly rises higher keeps PARTIAL credit,
        # ramping linearly to 0 at 3.5x resting height. So moderate skipping is permitted
        # but sustained ballistic flight (jumping) is still zeroed. All other modes keep the
        # original binary grounded/not-grounded rule.
        _skip_graded = (self.fitness_mode == "skip")
        _skip_hi     = ground_threshold * 1.75   # 2x -> 3.5x resting (ratio preserved if the 0.05 floor binds)

        # "skipbl": the same graded idea, but the allowance is measured in BODY LENGTHS rather
        # than as a multiple of resting height. A multiple-of-resting threshold is
        # morphology-dependent (tiny absolute clearance for a flat robot, generous for a tall
        # one); a body-length allowance judges every shape by the same physical standard.
        #   full credit  while COM <= resting + 0.5 * body_length
        #   linear ramp  to 0 between +0.5 and +1.0 body_length
        _bl_graded = (self.fitness_mode == "skipbl")
        _bl_lo     = settled_height + 0.5 * body_length
        _bl_hi     = settled_height + 1.0 * body_length

        # Score unit and distance (constructor's direction / divide_by). The defaults reproduce
        # the original +X / own-body-length arithmetic exactly.
        score_unit     = (self.workspace_voxels * self.voxel_size if self.divide_by == "workspace"
                          else body_length)
        initial_pos    = np.array(self.get_position(), dtype=float)
        initial_x      = float(initial_pos[0])

        def _progress():
            p = np.asarray(self.get_position(), dtype=float)
            if self.direction == "any":
                return float(np.linalg.norm(p - initial_pos)) / score_unit
            return (float(p[0]) - initial_x) / score_unit

        measure_steps  = int(simulation_time / self.default_timestep)
        check_step     = int(measure_steps * early_term_fraction)
        grounded_steps = 0
        heights        = []   # COM-z per step → gait descriptors (height, bounce)

        def _result(fit):
            if not return_descriptors:
                return fit
            if heights:
                h  = np.asarray(heights, dtype=float)
                d1 = float(h.mean()) / body_length   # mean COM height (body-lengths)
                d2 = float(h.std())  / body_length   # vertical bounce amplitude (body-lengths)
            else:
                d1 = d2 = 0.0
            return fit, (d1, d2)

        # A body with no active tendons has NO actuators — nothing drives it, so any
        # displacement is passive: it topples once and stops. Under the muscle-cost regime
        # that was the global optimum (zero muscle = zero penalty = full credit for the
        # fall), producing rigid statues that scored 0.54 BL while never locomoting.
        # A robot that cannot actuate is not locomoting, so it scores nothing.
        if self._actuator_count() == 0:
            return _result(0.0)

        energy = 0.0   # accumulated actuation effort (cost-of-transport proxy)

        def _shape(fbl, gf, steps):
            """Apply the selected fitness-shaping mode. All modes still reward forward
            (+X) body-lengths; they differ in what else they reward/penalise."""
            base = max(0.0, fbl)
            mode = self.fitness_mode
            if mode == "forward":            # raw forward distance, no ground penalty
                return base
            if mode == "efficiency":         # distance per unit actuation effort
                mean_force = (energy / max(steps, 1)) / max(int(self.model.nu), 1)
                return base * gf / (1.0 + 0.001 * mean_force)
            if mode == "stable":             # penalise vertical bounce (smooth gait)
                bounce = (float(np.std(heights)) / body_length) if heights else 0.0
                return base * gf / (1.0 + 5.0 * bounce)
            if mode == "skip":               # graded ground credit (gf computed with the
                return base * gf             # 2x->3.5x ramp above): skips OK, jumps zeroed
            if mode == "skipbl":             # as skip, but the allowance is body-length-relative
                return base * gf
            if mode == "musclecost":
                # Cheney 2013's "cost for actuated voxels" regime, normalised by the body's
                # OWN voxel count, i.e. the penalty is the MUSCLE FRACTION.
                #
                # Normalising by max_voxels instead (Cheney's literal formulation) is
                # degenerate here: it makes the penalty shrink with body size, so on top of
                # the body-length-normalised distance metric — which already favours small
                # robots — evolution simply collapses to the minimum body size and stays
                # 100% muscle. Measured on stage1_s1: corr(fitness, body_length) = -0.66,
                # top solutions were 20-28 voxels, all 100% muscle, and travelled LESS in
                # absolute terms than the larger champions they outscored.
                #
                # Muscle FRACTION is size-neutral: shrinking gains nothing, and the only way
                # to reduce the penalty is to adopt passive support tissue. That is exactly
                # the differentiation Cheney's Fig. 10 reports for this regime.
                penalty = min(1.0, self._n_actuated_voxels / max(self._n_voxels, 1))
                return base * gf * (1.0 - penalty)
            return base * gf                 # "directed" (default, unchanged)

        for step_idx in range(measure_steps):
            self.step()
            energy += float(np.sum(np.abs(self.data.actuator_force)))
            com_z = float(np.mean(self.data.xpos[1:nbody, 2]))
            heights.append(com_z)
            if _skip_graded:
                if com_z <= ground_threshold:
                    grounded_steps += 1.0
                elif com_z < _skip_hi:
                    grounded_steps += float((_skip_hi - com_z) / (_skip_hi - ground_threshold))
                # com_z >= _skip_hi -> +0 (ballistic flight earns no credit)
            elif _bl_graded:
                if com_z <= _bl_lo:
                    grounded_steps += 1.0
                elif com_z < _bl_hi:
                    grounded_steps += float((_bl_hi - com_z) / (_bl_hi - _bl_lo))
                # above a full body-length of clearance -> no credit
            elif com_z < ground_threshold:
                grounded_steps += 1

            if step_idx + 1 == check_step:
                progress = _progress()
                if progress < early_term_threshold:
                    ground_fraction = grounded_steps / (step_idx + 1)
                    return _result(_shape(progress, ground_fraction, step_idx + 1))

        ground_fraction = grounded_steps / measure_steps
        return _result(_shape(_progress(), ground_fraction, measure_steps))
