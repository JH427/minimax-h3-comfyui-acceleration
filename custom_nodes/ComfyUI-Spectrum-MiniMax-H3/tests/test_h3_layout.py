from __future__ import annotations

from types import SimpleNamespace

import pytest

from comfyui_spectrum_h3.minimax_h3 import branch_labels, target_segments


def test_target_segments_verify_native_audio_then_video_tail_order():
    layout = SimpleNamespace(
        seq_len=18,
        segments=[(0, 3, "text"), (3, 6, "ref_img"), (6, 10, "audio"), (10, 18, "video")],
    )
    assert target_segments(layout) == ((6, 10), (10, 18))


@pytest.mark.parametrize(
    "segments",
    [
        [(0, 2, "text"), (2, 6, "video"), (6, 8, "audio")],
        [(0, 2, "text"), (2, 4, "audio"), (5, 8, "video")],
        [(0, 2, "text"), (2, 4, "audio"), (4, 8, "video"), (8, 9, "ref_img")],
    ],
)
def test_invalid_target_layout_is_rejected(segments):
    with pytest.raises(RuntimeError):
        target_segments(SimpleNamespace(seq_len=segments[-1][1], segments=segments))


def test_branch_labels_require_matching_cond_and_uuid_vectors():
    assert branch_labels({"cond_or_uncond": [0, 1], "uuids": ["p", "n"]}) == ((0, "p"), (1, "n"))
    assert branch_labels({"cond_or_uncond": [0], "uuids": []}) is None
    assert branch_labels({}) is None
