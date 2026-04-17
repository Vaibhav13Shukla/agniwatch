"""Tests for spectral indices module using a small EE stub."""

import sys
import types


class FakeImage:
    def __init__(self, value=None, bands=None):
        self.value = value
        self.bands = bands or {}

    def normalizedDifference(self, band_names):
        b1 = self.bands[band_names[0]]
        b2 = self.bands[band_names[1]]
        return FakeImage(value=(b1 - b2) / (b1 + b2 + 1e-10))

    def rename(self, name):
        return FakeImage(bands={name: self.value if self.value is not None else next(iter(self.bands.values()))})

    def toFloat(self):
        return self

    def select(self, band):
        if isinstance(band, list):
            return FakeImage(bands={b: self.bands[b] for b in band})
        return FakeImage(value=self.bands[band])

    def subtract(self, other):
        return FakeImage(value=self.value - other.value)

    def add(self, other):
        if isinstance(other, FakeImage):
            return FakeImage(value=self.value + other.value)
        return FakeImage(value=self.value + other)

    def divide(self, other):
        if isinstance(other, FakeImage):
            return FakeImage(value=self.value / (other.value + 1e-10))
        return FakeImage(value=self.value / other)

    def pow(self, power):
        return FakeImage(value=self.value ** power)

    def abs(self):
        return FakeImage(value=abs(self.value))

    def sqrt(self):
        return FakeImage(value=self.value ** 0.5)


fake_ee = types.SimpleNamespace(Image=lambda v: FakeImage(value=float(v)), ImageCollection=None)
sys.modules.setdefault("ee", fake_ee)
sys.path.insert(0, "/home/vaibhav/agniwatch")

from core.indices import compute_bai, compute_dnbr, compute_nbr, compute_ndvi, compute_ndwi, compute_rdnbr


def test_compute_nbr():
    img = FakeImage(bands={"B8": 0.6, "B12": 0.1})
    nbr = compute_nbr(img)
    expected = (0.6 - 0.1) / (0.6 + 0.1)
    assert abs(nbr.bands["NBR"] - expected) < 1e-6


def test_compute_ndvi():
    img = FakeImage(bands={"B8": 0.7, "B4": 0.2})
    ndvi = compute_ndvi(img)
    expected = (0.7 - 0.2) / (0.7 + 0.2)
    assert abs(ndvi.bands["NDVI"] - expected) < 1e-6


def test_compute_ndwi():
    img = FakeImage(bands={"B3": 0.5, "B8": 0.2})
    ndwi = compute_ndwi(img)
    expected = (0.5 - 0.2) / (0.5 + 0.2)
    assert abs(ndwi.bands["NDWI"] - expected) < 1e-6


def test_compute_dnbr_and_rdnbr():
    dnbr = compute_dnbr(FakeImage(value=0.5), FakeImage(value=0.1))
    assert abs(dnbr.bands["dNBR"] - 0.4) < 1e-9

    rdnbr = compute_rdnbr(FakeImage(value=0.4), FakeImage(value=0.25))
    expected = 0.4 / (0.25 ** 0.5 + 1e-6)
    assert abs(rdnbr.bands["RdNBR"] - expected) < 1e-6


def test_compute_bai():
    img = FakeImage(bands={"B4": 0.2, "B8": 0.3})
    bai = compute_bai(img)
    expected = 1.0 / (((0.1 - 0.2) ** 2) + ((0.06 - 0.3) ** 2))
    assert abs(bai.bands["BAI"] - expected) < 1e-6


if __name__ == "__main__":
    test_compute_nbr()
    test_compute_ndvi()
    test_compute_ndwi()
    test_compute_dnbr_and_rdnbr()
    test_compute_bai()
    print("All index tests passed.")