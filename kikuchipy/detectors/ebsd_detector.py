# -*- coding: utf-8 -*-
# Copyright 2019-2020 The kikuchipy developers
#
# This file is part of kikuchipy.
#
# kikuchipy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# kikuchipy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kikuchipy. If not, see <http://www.gnu.org/licenses/>.

from typing import List, Optional, Tuple, Union

import numpy as np

from kikuchipy.projections import detector2reciprocal_lattice


class EBSDDetector:
    def __init__(
        self,
        shape: Tuple[int, int] = (1, 1),
        pixel_size: float = 1,
        binning: int = 1,
        tilt: float = 0,
        sample_tilt: float = 70,
        pcx: Union[np.ndarray, float] = 1.0,
        pcy: Union[np.ndarray, float] = 1.0,
        pcz: Union[np.ndarray, float] = 1.0,
        convention: Optional[str] = None,
    ):
        """Create an EBSD detector with a shape, pixel size, binning,
        and projection/pattern center(s) (PC(s)).

        Parameters
        ----------
        shape
            Number of detector rows and columns in pixels. Default is
            (1, 1).
        pixel_size
            Size of binned detector pixel in um, assuming a square pixel
            shape. Default is 1 um.
        binning
            Detector binning, i.e. how many pixels are binned into one.
            Default is 1, i.e. no binning.
        tilt
            Detector tilt from horizontal in degrees. Default is 0.
        sample_tilt
            Sample tilt from horizontal in degrees. Default is 70.
        pcx
            X coordinate(s) of the PC(s), from detector left, describing
            the location of the beam on the sample measured relative to
            the detection screen. Default is 1, i.e. at the right edge.
        pcy
            Y coordinate(s) of the PC(s), from detector top. Default is
            1, i.e. at the bottom edge.
        pcz
            Z coordinate(s) of the PC(s), distance from sample to
            detection screen. Default is 1.
        convention
            PC convention. If None (default), Bruker's convention is
            assumed.
        """
        self.shape = shape
        self.pixel_size = pixel_size
        self.binning = binning
        self.tilt = tilt
        self.sample_tilt = sample_tilt
        self.pcx = pcx
        self.pcy = pcy
        self.pcz = pcz
        self._set_pc_convention(convention)

    @property
    def nrows(self) -> int:
        """Number of rows in pixels."""
        return self.shape[0]

    @property
    def ncols(self) -> int:
        """Number of columns in pixels."""
        return self.shape[1]

    @property
    def size(self) -> int:
        """Number of pixels."""
        return self.nrows * self.ncols

    @property
    def height(self) -> float:
        """Detector height in microns."""
        return self.nrows * self.pixel_size

    @property
    def width(self) -> float:
        """Detector width in microns."""
        return self.ncols * self.pixel_size

    @property
    def aspect_ratio(self) -> float:
        """Number of detector rows divided by columns."""
        return self.nrows / self.ncols

    @property
    def shape_unbinned(self) -> Tuple[int, int]:
        """Unbinned detector shape in pixels."""
        return tuple(np.array(self.shape) * self.binning)

    @property
    def pc(self) -> np.ndarray:
        """All PC coordinates."""
        return np.stack((self.pcx, self.pcy, self.pcz))

    @pc.setter
    def pc(self, value: Union[np.ndarray, List, Tuple]):
        """Set all PC coordinates."""
        self.pcx, self.pcy, self.pcz = value

    @property
    def x_min(self) -> Union[np.ndarray, float]:
        """Left bound of detector in gnomonic projection."""
        return -self.aspect_ratio * (self.pcx / self.pcz)

    @property
    def x_max(self) -> Union[np.ndarray, float]:
        """Right bound of detector in gnomonic projection."""
        return self.aspect_ratio * (1 - self.pcx) / self.pcz

    @property
    def x_range(self) -> np.ndarray:
        """X detector limits in gnomonic projection."""
        return np.stack((self.x_min, self.x_max))

    @property
    def y_min(self) -> Union[np.ndarray, float]:
        """Top bound of detector in gnomonic projection."""
        return -(1 - self.pcy) / self.pcz

    @property
    def y_max(self) -> Union[np.ndarray, float]:
        """Bottom bound of detector in gnomonic projection."""
        return self.pcy / self.pcz

    @property
    def y_range(self) -> np.ndarray:
        """Y detector limits in gnomonic projection."""
        return np.stack((self.y_min, self.y_max))

    def __repr__(self) -> str:
        pc_mean = np.zeros(3)
        for i, pc in enumerate([self.pcx, self.pcy, self.pcz]):
            if isinstance(pc, np.ndarray):
                pc_mean[i] = pc.mean()
            elif pc is not None:
                pc_mean[i] = pc
        return (
            f"EBSDDetector {self.shape}\n  "
            f"pixel_size {self.pixel_size} um, "
            f"binning {self.binning}, "
            f"tilt {self.tilt}\n  "
            f"pcx {pc_mean[0]}, pcy {pc_mean[1]}, pcz {pc_mean[2]}"
        )

    def _set_pc_convention(self, convention: str):
        """Set appropriate PC based on vendor convention."""
        if convention is None or convention == "bruker":
            pass
        elif convention.lower() == "tsl":
            self.pcx, self.pcy, self.pcz = self._tsl2bruker()
        elif convention.lower() == "oxford":
            self.pcx, self.pcy, self.pcz = self._oxford2emsoft()
            self.pcx, self.pcy, self.pcz = self._emsoft2bruker()
        elif convention.lower() == "emsoft":
            self.pcx, self.pcy, self.pcz = self._emsoft2bruker()
        else:
            conventions = ["bruker", "emsoft", "oxford", "tsl"]
            raise ValueError(
                f"Projection center convention '{convention}' not among the "
                f"recognised conventions {conventions}."
            )

    def _bruker2emsoft(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from Bruker to EMsoft convention."""
        new_x = self.width * (self.pcx - 0.5)
        new_y = self.height * (0.5 - self.pcy)
        new_z = self.height * self.pixel_size * self.pcz
        return new_x, new_y, new_z

    def _emsoft2bruker(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from EMsoft to Bruker convention."""
        new_x = (self.pcx / self.width) + 0.5
        new_y = 0.5 - (self.pcy / self.height)
        new_z = self.pcz / (self.height * self.pixel_size)
        return new_x, new_y, new_z

    def _tsl2emsoft(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from EDAX TSL to EMsoft convention."""
        new_x = self.width * (self.pcx - 0.5)
        new_y = self.height * (0.5 - self.pcy)
        new_z = self.width * self.pixel_size * self.pcz
        return new_x, new_y, new_z

    def _emsoft2tsl(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from EMsoft to EDAX TSL convention."""
        new_x = (self.pcx / self.width) + 0.5
        new_y = 0.5 - (self.pcy / self.height)
        new_z = self.pcz / (self.width * self.pixel_size)
        return new_x, new_y, new_z

    def _tsl2bruker(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from EDAX TSL to Bruker convention."""
        return self.pcx, 1 - self.pcy, self.pcz

    def _bruker2tsl(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from Bruker to EDAX TSL convention."""
        return self.pcx, 1 - self.pcy, self.pcz

    def _oxford2emsoft(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert PC from Oxford to EMsoft convention."""
        new_x = self.width * (self.pcx - 0.5)
        new_y = self.height * (self.pcy - 0.5)
        new_z = self.width * self.pixel_size * self.pcz
        return new_x, new_y, new_z

    def to_emsoft(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return PC in the EMsoft convention."""
        return self._bruker2emsoft()

    def to_bruker(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return PC in the Bruker convention."""
        return self.pcx, self.pcy, self.pcz

    def to_tsl(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return PC in the EDAX TSL convention."""
        return self._bruker2tsl()

    def to_oxford(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return PC in the Oxford convention."""
        raise NotImplementedError
