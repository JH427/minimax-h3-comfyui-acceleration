from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import torch


@dataclass(slots=True)
class _HistoryEntry:
    coordinate: float
    feature_flat: torch.Tensor


@dataclass(slots=True)
class ForecasterSnapshot:
    history: list[_HistoryEntry]
    feature_shape: tuple[int, ...] | None
    feature_dtype: torch.dtype | None
    history_device: torch.device | None
    generation: int
    factor_generation: int
    design: torch.Tensor | None
    cholesky: torch.Tensor | None
    factorization_count: int
    jitter_attempts: int


class HistoryWeightForecaster:
    """Chebyshev ridge forecasting without full-feature FP32 coefficients.

    Persistent large tensors are model-dtype history snapshots on the configured
    storage device. Regression work is limited to K x (M + 1) design data and a
    (M + 1)^2 factorization.
    """

    def __init__(
        self,
        degree: int = 4,
        ridge_lambda: float = 0.1,
        max_history: int = 8,
        chunk_bytes: int = 32 * 1024 * 1024,
        history_storage: str = "system_ram",
    ) -> None:
        self.degree = int(degree)
        self.ridge_lambda = float(ridge_lambda)
        self.max_history = int(max_history)
        self.chunk_bytes = int(chunk_bytes)
        self.history_storage = str(history_storage)
        if self.degree < 1:
            raise ValueError("degree must be >= 1")
        if self.ridge_lambda < 0.0:
            raise ValueError("ridge_lambda must be >= 0")
        if self.max_history < max(2, self.degree + 1):
            raise ValueError("max_history is too small for the requested polynomial degree")
        if self.chunk_bytes < 4096:
            raise ValueError("chunk_bytes must be >= 4096")
        if self.history_storage not in {"system_ram", "vram"}:
            raise ValueError("history_storage must be 'system_ram' or 'vram'")
        self.reset()

    def reset(self) -> None:
        self._history: list[_HistoryEntry] = []
        self._feature_shape: tuple[int, ...] | None = None
        self._feature_dtype: torch.dtype | None = None
        self._history_device: torch.device | None = None
        self._generation = 0
        self._factor_generation = -1
        self._design: torch.Tensor | None = None
        self._cholesky: torch.Tensor | None = None
        self._factorization_count = 0
        self._jitter_attempts = 0
        self.last_prediction_chunk_count = 0
        self.last_prediction_max_fp32_elements = 0

    def snapshot(self) -> ForecasterSnapshot:
        return ForecasterSnapshot(
            history=list(self._history),
            feature_shape=self._feature_shape,
            feature_dtype=self._feature_dtype,
            history_device=self._history_device,
            generation=self._generation,
            factor_generation=self._factor_generation,
            design=self._design,
            cholesky=self._cholesky,
            factorization_count=self._factorization_count,
            jitter_attempts=self._jitter_attempts,
        )

    def restore(self, snapshot: ForecasterSnapshot) -> None:
        if not isinstance(snapshot, ForecasterSnapshot):
            raise TypeError("snapshot must be a ForecasterSnapshot")
        self._history = list(snapshot.history)
        self._feature_shape = snapshot.feature_shape
        self._feature_dtype = snapshot.feature_dtype
        self._history_device = snapshot.history_device
        self._generation = snapshot.generation
        self._factor_generation = snapshot.factor_generation
        self._design = snapshot.design
        self._cholesky = snapshot.cholesky
        self._factorization_count = snapshot.factorization_count
        self._jitter_attempts = snapshot.jitter_attempts
        self.last_prediction_chunk_count = 0
        self.last_prediction_max_fp32_elements = 0

    @property
    def history_length(self) -> int:
        return len(self._history)

    @property
    def feature_shape(self) -> tuple[int, ...] | None:
        return self._feature_shape

    @property
    def feature_dtype(self) -> torch.dtype | None:
        return self._feature_dtype

    @property
    def history_device(self) -> torch.device | None:
        return self._history_device

    @property
    def factorization_count(self) -> int:
        return self._factorization_count

    @property
    def jitter_attempts(self) -> int:
        return self._jitter_attempts

    @property
    def persistent_tensor_bytes(self) -> int:
        tensors = [entry.feature_flat for entry in self._history]
        tensors.extend(t for t in (self._design, self._cholesky) if t is not None)
        return sum(t.numel() * t.element_size() for t in tensors)

    @property
    def history_tensor_bytes(self) -> int:
        return sum(entry.feature_flat.numel() * entry.feature_flat.element_size() for entry in self._history)

    def ready(self, minimum: int | None = None) -> bool:
        required = max(2, self.degree + 1, int(minimum or 0))
        return len(self._history) >= required

    @staticmethod
    def chebyshev_design(coordinates: torch.Tensor, degree: int) -> torch.Tensor:
        x = coordinates.reshape(-1, 1).to(device="cpu", dtype=torch.float32)
        columns = [torch.ones_like(x)]
        if degree >= 1:
            columns.append(x)
        for _ in range(2, degree + 1):
            columns.append(2.0 * x * columns[-1] - columns[-2])
        return torch.cat(columns[: degree + 1], dim=1)

    def update(self, coordinate: float, feature: torch.Tensor, *, take_ownership: bool = False) -> None:
        if not torch.is_tensor(feature) or not feature.dtype.is_floating_point:
            raise ValueError("Spectrum history features must be floating-point tensors")
        shape = tuple(int(v) for v in feature.shape)
        if len(shape) < 2:
            raise ValueError("Spectrum history features must have a branch dimension and feature dimensions")
        if self._feature_shape is None:
            self._feature_shape = shape
            self._feature_dtype = feature.dtype
        elif shape != self._feature_shape:
            raise ValueError(f"feature shape changed from {self._feature_shape} to {shape}")
        elif feature.dtype != self._feature_dtype:
            raise ValueError(f"feature dtype changed from {self._feature_dtype} to {feature.dtype}")

        detached = feature.detach()
        storage_device = torch.device("cpu") if self.history_storage == "system_ram" else detached.device
        if self._history_device is None:
            self._history_device = storage_device
        elif storage_device != self._history_device:
            raise ValueError(f"history device changed from {self._history_device} to {storage_device}")

        if take_ownership and detached.device == storage_device and detached.is_contiguous():
            archived = detached.reshape(-1)
        else:
            archived = (
                detached.to(device=storage_device, dtype=self._feature_dtype, copy=True)
                .contiguous()
                .reshape(-1)
            )
        self._history.append(_HistoryEntry(float(coordinate), archived))
        if len(self._history) > self.max_history:
            self._history.pop(0)
        self._generation += 1
        self._design = None
        self._cholesky = None

    def _ensure_factorization(self) -> tuple[torch.Tensor, torch.Tensor]:
        if not self.ready():
            raise RuntimeError("Spectrum forecaster does not have enough actual history")
        if (
            self._factor_generation == self._generation
            and self._design is not None
            and self._cholesky is not None
        ):
            return self._design, self._cholesky

        coords = torch.tensor([entry.coordinate for entry in self._history], dtype=torch.float32)
        design = self.chebyshev_design(coords, self.degree)
        gram = design.transpose(0, 1) @ design
        eye = torch.eye(gram.shape[0], dtype=torch.float32)
        base = gram + self.ridge_lambda * eye
        diagonal_scale = max(float(gram.diag().abs().mean().item()), 1.0)
        jitters = (0.0, 1e-8, 1e-7, 1e-6, 1e-5)
        last_error: RuntimeError | None = None
        cholesky = None
        for attempt, multiplier in enumerate(jitters):
            try:
                cholesky = torch.linalg.cholesky(base + (diagonal_scale * multiplier) * eye)
                self._jitter_attempts += attempt
                break
            except RuntimeError as exc:
                last_error = exc
        if cholesky is None:
            raise RuntimeError("Spectrum ridge factorization failed after bounded jitter attempts") from last_error

        self._design = design
        self._cholesky = cholesky
        self._factor_generation = self._generation
        self._factorization_count += 1
        return design, cholesky

    def _spectral_weights(self, coordinate: float) -> torch.Tensor:
        design, cholesky = self._ensure_factorization()
        phi = self.chebyshev_design(torch.tensor([float(coordinate)]), self.degree)
        solved = torch.cholesky_solve(design.transpose(0, 1), cholesky)
        return (phi @ solved).reshape(-1)

    def spectral_weights(self, coordinate: float) -> torch.Tensor:
        return self._spectral_weights(coordinate)

    def _linear_weights(self, coordinate: float) -> torch.Tensor:
        weights = torch.zeros(len(self._history), dtype=torch.float32)
        if len(self._history) == 1:
            weights[-1] = 1.0
            return weights
        previous = self._history[-2].coordinate
        latest = self._history[-1].coordinate
        spacing = latest - previous
        if abs(spacing) <= 1e-12:
            weights[-1] = 1.0
            return weights
        ratio = (float(coordinate) - latest) / spacing
        weights[-2] = -ratio
        weights[-1] = 1.0 + ratio
        return weights

    def combined_weights(self, coordinate: float, blend_weight: float) -> torch.Tensor:
        blend = float(blend_weight)
        if not 0.0 <= blend <= 1.0:
            raise ValueError("blend_weight must be in [0, 1]")
        if blend <= 1e-12:
            return self._linear_weights(coordinate)
        spectral = self._spectral_weights(coordinate)
        if blend >= 1.0 - 1e-12:
            return spectral
        return blend * spectral + (1.0 - blend) * self._linear_weights(coordinate)

    def _chunk_elements(self, device: torch.device) -> int:
        target_bytes = self.chunk_bytes
        if device.type == "cuda" and torch.cuda.is_available():
            try:
                free_bytes, _ = torch.cuda.mem_get_info(device)
                target_bytes = min(target_bytes, max(4 * 1024 * 1024, int(free_bytes) // 32))
            except (RuntimeError, TypeError):
                pass
        return max(1024, target_bytes // torch.tensor([], dtype=torch.float32).element_size())

    def _normalize_rows(self, rows: Sequence[int] | None) -> tuple[int, ...]:
        if self._feature_shape is None:
            raise RuntimeError("Spectrum forecaster has no feature shape")
        branch_count = self._feature_shape[0]
        resolved = tuple(range(branch_count)) if rows is None else tuple(int(v) for v in rows)
        if not resolved:
            raise ValueError("row selection cannot be empty")
        if any(row < 0 or row >= branch_count for row in resolved):
            raise ValueError(f"row selection {resolved} is outside branch count {branch_count}")
        return resolved

    def predict(
        self,
        coordinate: float,
        blend_weight: float,
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        if self._feature_shape is None or self._feature_dtype is None:
            raise RuntimeError("Spectrum forecaster has no actual history")
        weights = self.combined_weights(coordinate, blend_weight)
        return self._predict_with_weights(weights, rows=rows, device=device, dtype=dtype)

    def predict_segments(
        self,
        coordinate: float,
        segment_blends: Sequence[tuple[int, int, float]],
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        weighted_segments = [
            (start, end, self.combined_weights(coordinate, blend_weight))
            for start, end, blend_weight in segment_blends
        ]
        return self._predict_with_segment_weights(
            weighted_segments,
            rows=rows,
            device=device,
            dtype=dtype,
        )

    def predict_one_point_hold(
        self,
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        if len(self._history) != 1:
            raise RuntimeError("one-point hold requires exactly one actual history entry")
        weights = torch.ones(1, dtype=torch.float32)
        return self._predict_with_weights(weights, rows=rows, device=device, dtype=dtype)

    def predict_latest_hold(
        self,
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        if not self._history:
            raise RuntimeError("latest hold requires at least one actual history entry")
        weights = torch.zeros(len(self._history), dtype=torch.float32)
        weights[-1] = 1.0
        return self._predict_with_weights(weights, rows=rows, device=device, dtype=dtype)

    def predict_with_weights(
        self,
        weights: torch.Tensor,
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        return self._predict_with_weights(weights, rows=rows, device=device, dtype=dtype)

    def predict_with_segment_weights(
        self,
        weighted_segments: Sequence[tuple[int, int, torch.Tensor]],
        *,
        rows: Sequence[int] | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        return self._predict_with_segment_weights(
            weighted_segments,
            rows=rows,
            device=device,
            dtype=dtype,
        )

    def _predict_with_weights(
        self,
        weights: torch.Tensor,
        *,
        rows: Sequence[int] | None,
        device: torch.device | str | None,
        dtype: torch.dtype | None,
    ) -> torch.Tensor:
        if self._feature_shape is None or self._feature_dtype is None:
            raise RuntimeError("Spectrum forecaster has no actual history")
        if len(self._feature_shape) < 2:
            raise RuntimeError("Spectrum forecaster feature shape is invalid")
        feature_rows = self._feature_shape[1] if len(self._feature_shape) >= 3 else 1
        return self._predict_with_segment_weights(
            ((0, feature_rows, weights),),
            rows=rows,
            device=device,
            dtype=dtype,
        )

    def _predict_with_segment_weights(
        self,
        weighted_segments: Sequence[tuple[int, int, torch.Tensor]],
        *,
        rows: Sequence[int] | None,
        device: torch.device | str | None,
        dtype: torch.dtype | None,
    ) -> torch.Tensor:
        if self._feature_shape is None or self._feature_dtype is None:
            raise RuntimeError("Spectrum forecaster has no actual history")
        feature_rows = self._feature_shape[1] if len(self._feature_shape) >= 3 else 1
        normalized_segments = []
        expected_start = 0
        for start, end, weights in weighted_segments:
            start = int(start)
            end = int(end)
            if start != expected_start or end <= start or end > feature_rows:
                raise ValueError("prediction segments must cover feature rows contiguously")
            if weights.ndim != 1 or weights.numel() != len(self._history):
                raise ValueError("prediction weights must match actual history length")
            normalized_segments.append((start, end, tuple(float(weight) for weight in weights.tolist())))
            expected_start = end
        if expected_start != feature_rows:
            raise ValueError("prediction segments must cover every feature row")

        resolved_rows = self._normalize_rows(rows)
        target_device = torch.device(device or "cpu")
        target_dtype = dtype or self._feature_dtype
        if not target_dtype.is_floating_point:
            raise ValueError("prediction dtype must be floating point")

        tail_shape = self._feature_shape[1:]
        tail_numel = 1
        for size in tail_shape:
            tail_numel *= size
        if len(self._feature_shape) >= 3:
            row_numel = 1
            for size in tail_shape[1:]:
                row_numel *= size
        else:
            row_numel = tail_numel
        result = torch.empty((len(resolved_rows), *tail_shape), device=target_device, dtype=target_dtype)
        result_flat = result.reshape(-1)
        self.last_prediction_chunk_count = 0
        self.last_prediction_max_fp32_elements = 0

        for target_row, source_row in enumerate(resolved_rows):
            source_base = source_row * tail_numel
            target_base = target_row * tail_numel
            for start, end, weight_scalars in normalized_segments:
                segment_start = start * row_numel
                segment_numel = (end - start) * row_numel
                chunk_elements = min(self._chunk_elements(target_device), segment_numel)
                for offset in range(0, segment_numel, chunk_elements):
                    length = min(chunk_elements, segment_numel - offset)
                    accumulator = torch.zeros(length, device=target_device, dtype=torch.float32)
                    for scalar, entry in zip(weight_scalars, self._history, strict=True):
                        if scalar == 0.0:
                            continue
                        source = entry.feature_flat.narrow(
                            0,
                            source_base + segment_start + offset,
                            length,
                        )
                        source_fp32 = source.to(device=target_device, dtype=torch.float32, non_blocking=False)
                        accumulator.add_(source_fp32, alpha=scalar)
                    result_flat.narrow(
                        0,
                        target_base + segment_start + offset,
                        length,
                    ).copy_(accumulator.to(target_dtype))
                    self.last_prediction_chunk_count += 1
                    self.last_prediction_max_fp32_elements = max(
                        self.last_prediction_max_fp32_elements, accumulator.numel()
                    )
        return result
