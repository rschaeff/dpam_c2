"""
Path resolution for DPAM pipeline output organization.

Supports two layouts:
- **Sharded** (default for new runs): Outputs organized into per-step subdirectories
- **Flat** (legacy): All files in a single working directory

Usage:
    resolver = PathResolver(working_dir, sharded=True)
    output = resolver.step_dir(3) / f'{prefix}.foldseek'
    input_fa = resolver.step_dir(1) / f'{prefix}.fa'
"""

from pathlib import Path


# Mapping from step number to subdirectory name
STEP_DIRS = {
    1: 'step01_prepare',
    2: 'step02_hhsearch',
    3: 'step03_foldseek',
    4: 'step04_filter',
    5: 'step05_map_ecod',
    6: 'step06_candidates',
    7: 'step07_dali',
    8: 'step08_analyze',
    9: 'step09_support',
    10: 'step10_filter_domains',
    11: 'step11_sse',
    12: 'step12_disorder',
    13: 'step13_parse',
    15: 'step15_domass_features',
    16: 'step16_domass_predict',
    17: 'step17_confident',
    18: 'step18_mapping',
    19: 'step19_merge_candidates',
    20: 'step20_extract',
    21: 'step21_compare',
    22: 'step22_merge',
    23: 'step23_predictions',
    24: 'step24_integrate',
}


class PathResolver:
    """Resolve file paths for sharded or flat directory layouts.

    In sharded mode, each pipeline step writes to its own subdirectory.
    In flat mode, all files go to the root working directory (legacy behavior).

    State files (.dpam_state.json, _batch_state.json) and user inputs
    (.cif, .json) always stay in the root directory regardless of mode.
    """

    def __init__(self, root_dir: Path, sharded: bool = True):
        self.root = Path(root_dir)
        self.sharded = sharded

    def step_dir(self, step_num: int) -> Path:
        """Return output directory for a pipeline step.

        Creates the directory if it doesn't exist (sharded mode only).
        In flat mode, returns root directory.
        """
        if not self.sharded:
            return self.root
        name = STEP_DIRS.get(step_num)
        if name is None:
            return self.root
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def results_dir(self) -> Path:
        """Return directory for final result files."""
        if not self.sharded:
            return self.root
        d = self.root / 'results'
        d.mkdir(parents=True, exist_ok=True)
        return d

    def batch_dir(self) -> Path:
        """Return directory for batch-mode shared resources."""
        if not self.sharded:
            return self.root
        d = self.root / '_batch'
        d.mkdir(parents=True, exist_ok=True)
        return d

    def state_file(self, prefix: str) -> Path:
        """Return per-protein state file path (always in root)."""
        return self.root / f'.{prefix}.dpam_state.json'

    def batch_state_file(self) -> Path:
        """Return batch state file path (always in root)."""
        return self.root / '_batch_state.json'

    @classmethod
    def detect_layout(cls, root_dir: Path) -> bool:
        """Detect whether a working directory uses sharded layout.

        Returns True if sharded layout detected (step01_prepare/ exists),
        False otherwise (flat layout).
        """
        return (Path(root_dir) / 'step01_prepare').is_dir()
