from __future__ import annotations

import torch

import comfyui_spectrum_h3.runtime as runtime_module


class _MpsLikeTensor:
    def __init__(self):
        self.device = torch.device("mps")
        self.calls = []

    def detach(self):
        self.calls.append(("detach",))
        return self

    def to(self, *args, **kwargs):
        device = kwargs.get("device")
        dtype = kwargs.get("dtype")
        if args:
            if len(args) != 1:
                raise AssertionError(f"unexpected to() arguments: {args!r}")
            if isinstance(args[0], torch.dtype):
                dtype = args[0]
            else:
                device = args[0]
        if device is not None and dtype is not None:
            raise TypeError("MPS cannot transfer to CPU and cast to float64 in one operation")
        if dtype is torch.float64 and self.device.type == "mps":
            raise TypeError("MPS does not support float64")
        if device is not None:
            self.device = torch.device(device)
            self.calls.append(("device", self.device.type))
        if dtype is not None:
            self.calls.append(("dtype", dtype))
        return self

    def reshape(self, *shape):
        self.calls.append(("reshape", shape))
        return self


def test_cpu_float64_conversion_moves_off_mps_before_casting(monkeypatch):
    source = _MpsLikeTensor()
    monkeypatch.setattr(runtime_module.torch, "as_tensor", lambda _value: source)

    result = runtime_module._as_cpu_float64_vector(object())

    assert result is source
    assert source.calls == [
        ("detach",),
        ("device", "cpu"),
        ("dtype", torch.float64),
        ("reshape", (-1,)),
    ]


def test_cpu_float64_conversion_preserves_values_and_flattens():
    source = torch.tensor([[1.5, -2.0]], dtype=torch.float16)

    result = runtime_module._as_cpu_float64_vector(source)

    assert result.device.type == "cpu"
    assert result.dtype is torch.float64
    assert result.shape == (2,)
    torch.testing.assert_close(result, torch.tensor([1.5, -2.0], dtype=torch.float64))
