"""Resolution test (throwaway): does higher voxel resolution help flex locomotion?
Monkeypatches grid=30^3, cap=800 in THIS process only (parent decodes bodies; workers
consume the decoded grids), then runs a short flex MAP-Elites. Compare max fitness to
flex_qd_v1's ~0.0275 BL plateau at the standard 20^3/300."""
import src.evolution.cppn_genome as cg
import src.evolution.genome_config as gc

NEW, CAP = (30, 30, 30), 800
cg.VOXEL_GRID_SHAPE = NEW; cg.MAX_VOXELS_PER_ROBOT = CAP
gc.VOXEL_GRID_SHAPE = NEW; gc.MAX_VOXELS_PER_ROBOT = CAP

from run_tendon_evolution import run_map_elites

if __name__ == "__main__":
    run_map_elites(
        population_size=20, generations=30, sim_time=2.0, settle_time=0.3,
        actuation_freq=7.0, actuation_amp=0.6, n_workers=4,
        name="flex_res30", seed=5, resume=False, use_flex=True,
    )
