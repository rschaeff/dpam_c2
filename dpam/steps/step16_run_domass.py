"""
Step 16: Run DOMASS Neural Network

Run TensorFlow model to predict probability that each domain-ECOD pair is correct.

Input:
    - {prefix}.step15_features: Features for ML model (17 features + metadata)
    - domass_epo29 checkpoint: Trained TensorFlow model

Output:
    - {prefix}.step16_predictions: ML predictions with probabilities

Model Architecture:
    Input: 13 features (float32)
    Hidden Layer: 64 neurons, ReLU activation
    Output: 2-class softmax (incorrect=0, correct=1)

Features Used (13 of 17):
    Columns 5-17 from step 15 output:
    - domain_length, helix_count, strand_count
    - hh_prob, hh_cov, hh_rank
    - dali_zscore, dali_qscore, dali_ztile, dali_qtile, dali_rank
    - consensus_diff, consensus_cov

Algorithm:
    1. Load all feature rows from step 15
    2. Extract 13 numerical features per row
    3. Batch into groups of 100
    4. Run TensorFlow model inference
    5. Extract probability of class 1 (correct assignment)
    6. Write results with all input features + DPAM probability
"""

from pathlib import Path
from typing import List, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger(__name__)


class DomassModel:
    """Reusable DOMASS TensorFlow model session.

    Loads the model graph and checkpoint once. Call predict() for each protein's
    features. Use as context manager or call close() when done.

    Usage:
        with DomassModel(model_path) as model:
            for protein in proteins:
                predictions = model.predict(features)
    """

    def __init__(self, model_path: Path):
        try:
            import tensorflow as tf
        except ImportError:
            raise ImportError(
                "TensorFlow not installed. Install with: pip install tensorflow"
            )

        self._tf = tf
        self.batch_size = 100

        # Disable TensorFlow warnings and eager execution (TF2 compat)
        tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
        tf.compat.v1.disable_eager_execution()

        # Build model graph
        tf.compat.v1.reset_default_graph()
        self._sess = tf.compat.v1.Session()

        with tf.name_scope('input'):
            self._inputs = tf.compat.v1.placeholder(
                dtype=tf.float32,
                shape=(self.batch_size, 13),
                name='inputs'
            )

        # Hidden layer (must match checkpoint: dense/kernel, dense/bias)
        hidden = tf.compat.v1.layers.dense(
            self._inputs,
            64,
            activation=tf.nn.relu,
            name='dense'
        )

        # Output layer (must match checkpoint: dense_1/kernel, dense_1/bias)
        logits = tf.compat.v1.layers.dense(
            hidden,
            2,
            activation=None,
            name='dense_1'
        )

        self._preds = tf.nn.softmax(logits, name='predictions')

        # Load checkpoint
        saver = tf.compat.v1.train.Saver()
        saver.restore(self._sess, str(model_path))

        logger.info(f"Loaded DOMASS model from {model_path}")

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Run inference on feature matrix.

        Args:
            features: Array of shape (N, 13)

        Returns:
            Probability array (N,) for class 1 (correct assignment)
        """
        n_samples = len(features)
        batch_size = self.batch_size
        all_predictions = []

        if n_samples >= batch_size:
            # Process full batches
            n_batches = n_samples // batch_size

            for i in range(n_batches):
                batch_features = features[i * batch_size : (i + 1) * batch_size]
                batch_preds = self._sess.run(
                    self._preds, feed_dict={self._inputs: batch_features}
                )

                # Extract probability of class 1
                for j in range(batch_size):
                    all_predictions.append(batch_preds[j, 1])

                if i % 1000 == 0 and i > 0:
                    logger.info(f"Processed {i * batch_size}/{n_samples} samples")

            # Handle remaining samples
            remaining = n_samples - (n_batches * batch_size)
            if remaining > 0:
                # Pad with copies to reach batch size
                last_batch = features[n_batches * batch_size:]
                padding = features[:batch_size - remaining]
                padded_batch = np.vstack([last_batch, padding])

                batch_preds = self._sess.run(
                    self._preds, feed_dict={self._inputs: padded_batch}
                )

                # Only use predictions for actual samples
                for j in range(remaining):
                    all_predictions.append(batch_preds[j, 1])

        else:
            # Less than one batch - tile/repeat to reach batch size (matches v1.0)
            fold = batch_size // n_samples + 1
            pseudo_features = np.tile(features, (fold, 1))
            padded_batch = pseudo_features[:batch_size]

            batch_preds = self._sess.run(
                self._preds, feed_dict={self._inputs: padded_batch}
            )

            # Extract predictions for actual samples only
            for j in range(n_samples):
                all_predictions.append(batch_preds[j, 1])

        return np.array(all_predictions)

    def close(self):
        """Close the TensorFlow session and release resources."""
        if self._sess is not None:
            self._sess.close()
            self._sess = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def load_features(feature_file: Path) -> Tuple[List[List[str]], np.ndarray]:
    """
    Load features from step 15 output.

    Args:
        feature_file: Step 15 features file

    Returns:
        Tuple of (metadata rows, feature matrix)
        - metadata: List of [domain, range, tgroup, ecod, ...metadata...]
        - features: Array of shape (N, 13) with numerical features
    """
    metadata = []
    features = []

    with open(feature_file, 'r') as f:
        for i, line in enumerate(f):
            if i == 0:  # Skip header
                continue

            parts = line.strip().split('\t')
            if len(parts) < 17:
                continue

            try:
                # Metadata (columns 0-3, 17-22)
                meta_row = [
                    parts[0],   # domain name
                    parts[1],   # domain range
                    parts[2],   # tgroup
                    parts[3],   # ecod id
                    parts[17],  # HH hit name
                    parts[18],  # DALI hit name
                    parts[19],  # DALI rot1
                    parts[20],  # DALI rot2
                    parts[21],  # DALI rot3
                    parts[22] if len(parts) > 22 else 'na'  # DALI trans
                ]
                metadata.append(meta_row)

                # Features (columns 4-16: 13 numerical features)
                feature_row = [
                    float(parts[4]),   # domain_length
                    float(parts[5]),   # helix_count
                    float(parts[6]),   # strand_count
                    float(parts[7]),   # hh_prob
                    float(parts[8]),   # hh_coverage
                    float(parts[9]),   # hh_rank
                    float(parts[10]),  # dali_zscore
                    float(parts[11]),  # dali_qscore
                    float(parts[12]),  # dali_ztile
                    float(parts[13]),  # dali_qtile
                    float(parts[14]),  # dali_rank
                    float(parts[15]),  # consensus_diff
                    float(parts[16])   # consensus_cov
                ]
                features.append(feature_row)

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed feature line {i}: {e}")
                continue

    return metadata, np.array(features, dtype=np.float32)


def run_domass_model(
    features: np.ndarray,
    model_path: Path
) -> np.ndarray:
    """
    Run DOMASS TensorFlow model.

    Creates a temporary model session, runs inference, and closes.
    For batch processing multiple proteins, use DomassModel directly
    to avoid per-call model loading overhead (~22s).

    Args:
        features: Feature matrix (N, 13)
        model_path: Path to model checkpoint (without extension)

    Returns:
        Probability array (N,) for class 1 (correct assignment)
    """
    with DomassModel(model_path) as model:
        return model.predict(features)


def run_step16(
    prefix: str,
    working_dir: Path,
    data_dir: Path,
    model: Optional[DomassModel] = None,
    **kwargs
) -> bool:
    """
    Run DOMASS neural network for ECOD classification.

    Args:
        prefix: Structure identifier
        working_dir: Working directory containing input/output
        data_dir: Reference data directory
        model: Pre-loaded DomassModel instance for batch processing.
               If None, loads model from checkpoint (default single-protein behavior).
        **kwargs: Additional arguments (unused)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Step 16: Running DOMASS model for {prefix}")

    # Input file
    feature_file = working_dir / f"{prefix}.step15_features"

    if not feature_file.exists():
        logger.info(f"No features found for {prefix}")
        return True

    # Model checkpoint (only needed if no pre-loaded model)
    if model is None:
        model_path = data_dir / "domass_epo29"

        if not model_path.with_suffix('.meta').exists():
            logger.error(f"Model checkpoint not found: {model_path}")
            logger.error(f"Expected files: {model_path}.meta, {model_path}.index, {model_path}.data-*")
            return False

    # Load features
    logger.info("Loading features...")
    metadata, features = load_features(feature_file)

    if len(metadata) == 0:
        logger.info(f"No feature rows found for {prefix}")
        return True

    logger.info(f"Loaded {len(metadata)} feature rows")

    # Run model
    logger.info("Running TensorFlow model...")
    try:
        if model is not None:
            predictions = model.predict(features)
        else:
            predictions = run_domass_model(features, model_path)
    except Exception as e:
        logger.error(f"Model inference failed: {e}")
        logger.exception("TensorFlow error details:")
        return False

    logger.info(f"Generated {len(predictions)} predictions")

    # Write results
    output_file = working_dir / f"{prefix}.step16_predictions"

    with open(output_file, 'w') as f:
        # Write header
        f.write("Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\t"
                "HH_prob\tHH_cov\tHH_rank\t"
                "DALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\t"
                "Consensus_diff\tConsensus_cov\t"
                "HH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\n")

        # Write predictions
        for i, (meta, feat, pred) in enumerate(zip(metadata, features, predictions)):
            f.write(
                f"{meta[0]}\t{meta[1]}\t{meta[2]}\t{meta[3]}\t"  # Domain, Range, Tgroup, ECOD
                f"{pred:.4f}\t"  # DPAM probability
                f"{feat[3]:.3f}\t{feat[4]:.3f}\t{feat[5]:.2f}\t"  # HH prob, cov, rank
                f"{feat[6]:.3f}\t{feat[7]:.3f}\t{feat[8]:.3f}\t{feat[9]:.3f}\t{feat[10]:.2f}\t"  # DALI scores
                f"{feat[11]:.2f}\t{feat[12]:.3f}\t"  # Consensus
                f"{meta[4]}\t{meta[5]}\t{meta[6]}\t{meta[7]}\t{meta[8]}\t{meta[9]}\n"  # Metadata
            )

    logger.info(f"Step 16 complete: predictions written to {output_file.name}")

    # Summary statistics
    prob_stats = {
        'min': float(np.min(predictions)),
        'max': float(np.max(predictions)),
        'mean': float(np.mean(predictions)),
        'median': float(np.median(predictions))
    }

    logger.info(f"  Probability range: {prob_stats['min']:.3f} - {prob_stats['max']:.3f}")
    logger.info(f"  Mean probability: {prob_stats['mean']:.3f}")
    logger.info(f"  Median probability: {prob_stats['median']:.3f}")

    high_conf = np.sum(predictions >= 0.6)
    logger.info(f"  High confidence (≥0.6): {high_conf}/{len(predictions)} ({100*high_conf/len(predictions):.1f}%)")

    return True
