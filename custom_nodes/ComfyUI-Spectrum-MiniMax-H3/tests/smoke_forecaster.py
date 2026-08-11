from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from comfyui_spectrum_h3.forecast import HistoryWeightForecaster


def main() -> None:
    torch.manual_seed(7)
    forecaster = HistoryWeightForecaster(degree=4, ridge_lambda=0.1, max_history=8)
    coordinates = torch.linspace(-1.0, 0.2, 5)
    for coordinate in coordinates:
        feature = torch.stack(
            [
                torch.sin(coordinate * torch.arange(1, 13)).reshape(3, 4),
                torch.cos(coordinate * torch.arange(1, 13)).reshape(3, 4),
            ]
        ).to(torch.float16)
        forecaster.update(float(coordinate), feature)
    prediction = forecaster.predict(0.5, blend_weight=0.5)
    assert prediction.shape == (2, 3, 4)
    assert prediction.dtype == torch.float16
    assert torch.isfinite(prediction).all()
    assert forecaster.persistent_tensor_bytes < forecaster.history_tensor_bytes + 4096
    print("Spectrum H3 forecaster smoke test passed")


if __name__ == "__main__":
    main()
