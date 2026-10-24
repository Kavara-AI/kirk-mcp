"""Binding of one run to its release, configuration, ordered inputs, and outputs.

The reference comparison lives only in ``stamp_references``. Admission of
cadence, loader, and model does not satisfy that comparison.
"""

import hashlib
import json

from kirk_runs.errors import RunsError


def inputs_digest(inputs):
    """Digest of inputs in list order. Object keys are canonical; order is not sorted away."""
    payload = json.dumps(
        inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stamp_references(probed_release_id, computing_release_ids):
    """Refuse when the computing release disagrees with the probed release.

    This function does not inspect configuration, inputs, or output values.
    """
    if isinstance(computing_release_ids, str):
        computing_ids = [computing_release_ids]
    else:
        computing_ids = list(computing_release_ids)
    mismatch = next((item for item in computing_ids if item != probed_release_id), None)
    if not computing_ids or mismatch is not None:
        raise RunsError(
            "reference_mismatch",
            409,
            {
                "probed_release_id": probed_release_id,
                "computing_release_id": mismatch,
            },
        )


def assert_same_inputs(expected_digest, inputs):
    """Refuse when presented inputs are not the consumed order."""
    if not isinstance(inputs, list):
        raise RunsError("inputs_digest_mismatch", 422)
    try:
        digest = inputs_digest(inputs)
    except UnicodeError:
        raise RunsError("inputs_digest_mismatch", 422)
    if digest != expected_digest:
        raise RunsError("inputs_digest_mismatch", 422)
