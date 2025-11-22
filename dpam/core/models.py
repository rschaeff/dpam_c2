"""
Core data models for DPAM pipeline.

Type-safe dataclasses representing structures, domains, hits, and analysis results.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import numpy as np
from enum import Enum


class PipelineStep(Enum):
    """Pipeline execution steps"""
    PREPARE = 1
    HHSEARCH = 2
    FOLDSEEK = 3
    FILTER_FOLDSEEK = 4
    MAP_ECOD = 5
    DALI_CANDIDATES = 6
    ITERATIVE_DALI = 7
    ANALYZE_DALI = 8
    GET_SUPPORT = 9
    FILTER_DOMAINS = 10
    SSE = 11
    DISORDER = 12
    PARSE_DOMAINS = 13
    # Step 14 is duplicate of step 13 in v1.0
    PREPARE_DOMASS = 15
    RUN_DOMASS = 16
    GET_CONFIDENT = 17
    GET_MAPPING = 18
    GET_MERGE_CANDIDATES = 19
    EXTRACT_DOMAINS = 20
    COMPARE_DOMAINS = 21
    MERGE_DOMAINS = 22
    GET_PREDICTIONS = 23
    INTEGRATE_RESULTS = 24
    GENERATE_PDBS = 25


@dataclass
class Structure:
    """Parsed protein structure with coordinates and sequence"""
    prefix: str
    sequence: str
    residue_coords: Dict[int, np.ndarray]  # resid -> [N_atoms, 3] coordinates
    residue_ids: List[int]
    chain_id: str = 'A'
    atom_names: Dict[int, List[str]] = field(default_factory=dict)  # resid -> [atom_name1, atom_name2, ...]
    atom_elements: Dict[int, List[str]] = field(default_factory=dict)  # resid -> [element1, element2, ...]
    
    def __len__(self) -> int:
        return len(self.sequence)
    
    def get_ca_coords(self) -> Dict[int, np.ndarray]:
        """Extract CA coordinates only (for distance calculations)"""
        # This will be implemented in structure.py
        pass


@dataclass
class PAEMatrix:
    """Predicted Aligned Error matrix from AlphaFold"""
    matrix: np.ndarray  # [N, N] array
    length: int
    
    @classmethod
    def from_json(cls, json_data: dict) -> 'PAEMatrix':
        """Parse PAE from AlphaFold JSON output"""
        # Handle two formats
        if 'predicted_aligned_error' in json_data:
            pae_list = json_data['predicted_aligned_error']
            matrix = np.array(pae_list)
            length = len(matrix)
        elif 'distance' in json_data:
            residue1s = json_data['residue1']
            residue2s = json_data['residue2']
            distances = json_data['distance']
            length = max(max(residue1s), max(residue2s))
            matrix = np.zeros((length, length))
            for res1, res2, dist in zip(residue1s, residue2s, distances):
                matrix[res1-1, res2-1] = dist
        else:
            raise ValueError("Unrecognized PAE format")
        
        return cls(matrix=matrix, length=length)
    
    def get_error(self, res1: int, res2: int) -> float:
        """Get PAE between two residues (1-indexed)"""
        return self.matrix[res1-1, res2-1]


@dataclass
class SequenceHit:
    """Sequence-based domain hit from HHsearch"""
    ecod_num: str
    ecod_id: str
    family: str
    probability: float
    coverage: float
    ecod_length: int
    query_range: str  # e.g., "10-50,60-100"
    template_range: str
    
    def parse_query_residues(self) -> Set[int]:
        """Parse query range string into residue set"""
        residues = set()
        for seg in self.query_range.split(','):
            if '-' in seg:
                start, end = map(int, seg.split('-'))
                residues.update(range(start, end + 1))
            else:
                residues.add(int(seg))
        return residues


@dataclass
class StructureHit:
    """Structure-based domain hit from DALI"""
    hit_name: str
    ecod_num: str
    ecod_id: str
    family: str
    z_score: float
    q_score: float
    z_percentile: float
    q_percentile: float
    rank: float
    best_seq_prob: float
    best_seq_cov: float
    query_range: str
    template_range: str
    filtered_range: str  # After gap filtering
    
    def parse_query_residues(self) -> Set[int]:
        """Parse filtered range into residue set"""
        residues = set()
        for seg in self.filtered_range.split(','):
            if '-' in seg:
                start, end = map(int, seg.split('-'))
                residues.update(range(start, end + 1))
            else:
                residues.add(int(seg))
        return residues


@dataclass
class Domain:
    """Final parsed domain definition"""
    domain_id: str  # e.g., "D1", "D2"
    residue_range: str  # e.g., "10-50,60-100"
    residues: Set[int]
    mean_position: float
    length: int
    
    @classmethod
    def from_residues(cls, domain_id: str, residues: List[int]) -> 'Domain':
        """Create domain from residue list"""
        from dpam.utils.ranges import residues_to_range
        residues_set = set(residues)
        residue_range = residues_to_range(sorted(residues))
        mean_pos = np.mean(residues)
        return cls(
            domain_id=domain_id,
            residue_range=residue_range,
            residues=residues_set,
            mean_position=mean_pos,
            length=len(residues_set)
        )


@dataclass
class SecondaryStructure:
    """Secondary structure annotation"""
    residue_id: int
    amino_acid: str
    sse_id: Optional[int]  # None if not in SSE
    sse_type: str  # 'H' (helix), 'E' (strand), 'C' (coil)


@dataclass
class DisorderRegion:
    """Predicted disordered region"""
    residues: Set[int]
    
    def __contains__(self, residue_id: int) -> bool:
        return residue_id in self.residues


@dataclass
class FoldseekHit:
    """Raw Foldseek alignment hit"""
    ecod_num: str
    evalue: float
    query_start: int
    query_end: int
    
    def get_query_residues(self) -> Set[int]:
        return set(range(self.query_start, self.query_end + 1))


@dataclass
class HHSearchAlignment:
    """HHsearch alignment details"""
    hit_id: str
    probability: float
    evalue: float
    score: float
    aligned_cols: int
    identities: str
    similarity: str
    sum_probs: float
    query_start: int
    query_end: int
    query_seq: str
    template_start: int
    template_end: int
    template_seq: str


@dataclass
class DALIAlignment:
    """DALI structural alignment"""
    hit_name: str
    ecod_num: str
    z_score: float
    n_aligned: int
    query_length: int
    template_length: int
    alignments: List[Tuple[int, int]]  # [(query_resid, template_resid), ...]
    
    def get_query_residues(self) -> List[int]:
        return [q for q, t in self.alignments]


@dataclass
class PipelineState:
    """Track pipeline execution state for checkpointing"""
    prefix: str
    working_dir: Path
    completed_steps: Set[PipelineStep] = field(default_factory=set)
    failed_steps: Dict[PipelineStep, str] = field(default_factory=dict)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def mark_complete(self, step: PipelineStep) -> None:
        """Mark a step as completed"""
        self.completed_steps.add(step)
        if step in self.failed_steps:
            del self.failed_steps[step]
    
    def mark_failed(self, step: PipelineStep, error: str) -> None:
        """Mark a step as failed"""
        self.failed_steps[step] = error
    
    def is_complete(self, step: PipelineStep) -> bool:
        """Check if step is already completed"""
        return step in self.completed_steps
    
    def save(self, path: Path) -> None:
        """Save state to JSON file"""
        import json
        state_dict = {
            'prefix': self.prefix,
            'working_dir': str(self.working_dir),
            'completed_steps': [s.name for s in self.completed_steps],
            'failed_steps': {s.name: err for s, err in self.failed_steps.items()},
            'metadata': self.metadata
        }
        with open(path, 'w') as f:
            json.dump(state_dict, f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'PipelineState':
        """Load state from JSON file"""
        import json
        with open(path, 'r') as f:
            state_dict = json.load(f)
        
        return cls(
            prefix=state_dict['prefix'],
            working_dir=Path(state_dict['working_dir']),
            completed_steps={PipelineStep[s] for s in state_dict['completed_steps']},
            failed_steps={PipelineStep[s]: err for s, err in state_dict['failed_steps'].items()},
            metadata=state_dict['metadata']
        )


@dataclass
class ReferenceData:
    """ECOD reference database"""
    ecod_lengths: Dict[str, Tuple[str, int]]  # ecod_num -> (ecod_key, length)
    ecod_norms: Dict[str, float]  # ecod_num -> norm_value
    ecod_pdbmap: Dict[str, Tuple[str, str, List[int]]]  # pdbchain -> (ecod_num, chainid, residues)
    ecod_domain_info: Dict[str, Tuple[List[float], List[float]]]  # ecod_num -> (zscores, qscores)
    ecod_weights: Dict[str, Dict[int, float]]  # ecod_num -> {position: weight}
    ecod_metadata: Dict[str, Tuple[str, str]]  # ecod_num -> (ecod_id, family)
    
    @classmethod
    def load(cls, data_dir: Path) -> 'ReferenceData':
        """Load all ECOD reference data"""
        from dpam.io.reference_data import load_ecod_data
        return load_ecod_data(data_dir)
