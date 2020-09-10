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

import numpy as np
import pytest

from kikuchipy.detectors import EBSDDetector


class TestEBSDDetector:
    def test_init(self, pc1):
        """Initialization works."""
        shape = (1, 2)
        px_size = 3
        binning = 4
        tilt = 5
        det = EBSDDetector(
            shape=shape, px_size=px_size, binning=binning, tilt=tilt, pc=pc1,
        )
        assert det.shape == shape
        assert det.aspect_ratio == 0.5

    @pytest.mark.parametrize(
        "nav_shape, desired_nav_shape, desired_nav_dim",
        [
            ((), (1,), 1),
            ((1,), (1,), 1),
            ((10, 1), (10,), 1),
            ((10, 10, 1), (10, 10), 2),
        ],
    )
    def test_nav_shape_dim(
        self, pc1, nav_shape, desired_nav_shape, desired_nav_dim
    ):
        """Navigation shape and dimension is derived correctly from PC shape."""
        det = EBSDDetector(pc=np.tile(pc1, nav_shape))
        assert det.navigation_shape == desired_nav_shape
        assert det.navigation_dimension == desired_nav_dim

    @pytest.mark.parametrize("pc_type", [list, tuple, np.asarray])
    def test_pc_initialization(self, pc1, pc_type):
        """Initialize PC of valid types."""
        det = EBSDDetector(pc=pc_type(pc1))
        assert isinstance(det.pc, np.ndarray)

    @pytest.mark.parametrize(
        (
            "shape, px_size, binning, pc, ssd, width, height, size, "
            "shape_unbinned, px_size_binned"
        ),
        [
            # fmt: off
            (
                (60, 60), 70, 8, [1, 1, 0.5], 16800, 33600, 33600, 3600,
                (480, 480), 560,
            ),
            (
                (60, 60), 70, 8, [1, 1, 0.7], 23520, 33600, 33600, 3600,
                (480, 480), 560,
            ),
            (
                (480, 460), 70, 0.5, [1, 1, 0.7], 11760, 16100, 16800, 220800,
                (240, 230), 35,
            ),
            (
                (340, 680), 40, 2, [1, 1, 0.7], 19040, 54400, 27200, 231200,
                (680, 1360), 80,
            ),
            # fmt: on
        ],
    )
    def test_detector_dimensions(
        self,
        shape,
        px_size,
        binning,
        pc,
        ssd,
        width,
        height,
        size,
        shape_unbinned,
        px_size_binned,
    ):
        """Initialization yields expected derived values."""
        detector = EBSDDetector(
            shape=shape, px_size=px_size, binning=binning, pc=pc
        )
        assert detector.specimen_scintillator_distance == ssd
        assert detector.width == width
        assert detector.height == height
        assert detector.size == size
        assert detector.shape_unbinned == shape_unbinned
        assert detector.px_size_binned == px_size_binned

    @pytest.mark.parametrize(
        "pc, convention, bruker, tsl, oxford, emsoft",
        # fmt: off
        [
            (
                [3.4848, 114.2016, 15767.7], "emsoft",
                [0.50726, 0.26208, 0.55489], [0.50726, 0.73792, 0.55489],
                [0.50726, 0.73792, 0.55489], [3.4848, 114.2016, 15767.7],
            )
        ],
        # fmt: on
    )
    def test_pc_conversions(self, pc, convention, bruker, tsl, oxford, emsoft):
        """Conversions between PC conventions."""
        detector = EBSDDetector(
            shape=(480, 480),
            binning=1,
            px_size=59.2,
            pc=pc,
            convention=convention,
        )
        assert np.allclose(detector.pc, bruker, atol=1e-4)
        assert np.allclose(detector.to_bruker(), bruker, atol=1e-4)
        assert np.allclose(detector.to_emsoft(), emsoft, atol=1e-4)
        assert np.allclose(detector.to_tsl(), tsl, atol=1e-4)

    def test_repr(self, pc1):
        """Expected string representation."""
        assert repr(
            EBSDDetector(shape=(1, 2), px_size=3, binning=4, tilt=5, pc=pc1)
        ) == (
            "EBSDDetector (1, 2), px_size 3 um, binning 4, tilt 5, pc "
            "(0.421, 0.779, 0.505)"
        )

    def test_deepcopy(self, pc1):
        """Yields the expected parameters and an actual deep copy."""
        detector1 = EBSDDetector(pc=pc1)
        detector2 = detector1.deepcopy()
        detector1.pcx += 0.1
        assert np.allclose(detector1.pcx, 0.521)
        assert np.allclose(detector2.pcx, 0.421)

    def test_set_pc_coordinates(self, pc1):
        """Returns desired arrays with desired shapes."""
        ny, nx = (2, 3)
        nav_shape = (ny, nx)
        n = ny * nx
        detector = EBSDDetector(pc=np.tile(pc1, nav_shape + (1,)))
        assert detector.navigation_shape == nav_shape

        new_pc = np.zeros(nav_shape + (3,))
        new_pc[..., 0] = pc1[0] * 0.01 * np.arange(n).reshape(nav_shape)
        new_pc[..., 1] = pc1[1] * 0.01 * np.arange(n).reshape(nav_shape)
        new_pc[..., 2] = pc1[2] * 0.01 * np.arange(n).reshape(nav_shape)
        detector.pcx = new_pc[..., 0]
        detector.pcy = new_pc[..., 1]
        detector.pcz = new_pc[..., 2]
        assert np.allclose(detector.pc, new_pc)

    @pytest.mark.parametrize(
        "pc, desired_pc_average",
        [
            ([0.1234, 0.1235, 0.1234], [0.1230, 0.1240, 0.1230]),
            (np.arange(30).reshape((2, 5, 3)), [13.5, 14.5, 15.5]),
            (np.arange(30).reshape((10, 3)), [13.5, 14.5, 15.5]),
        ],
    )
    def test_pc_average(self, pc, desired_pc_average):
        """Calculation of PC average."""
        assert np.allclose(EBSDDetector(pc=pc).pc_average, desired_pc_average)

    @pytest.mark.parametrize(
        "pc, desired_nav_shape, desired_nav_ndim",
        [
            (np.arange(30).reshape((2, 5, 3)), (5, 2), 2),
            (np.arange(30).reshape((5, 2, 3)), (10, 1), 2),
            (np.arange(30).reshape((2, 5, 3)), (10,), 1),
        ],
    )
    def test_set_navigation_shape(
        self, pc, desired_nav_shape, desired_nav_ndim
    ):
        """Change shape of PC array."""
        detector = EBSDDetector(pc=pc)
        detector.navigation_shape = desired_nav_shape
        assert detector.navigation_shape == desired_nav_shape
        assert detector.navigation_dimension == desired_nav_ndim
        assert detector.pc.shape == desired_nav_shape + (3,)

    def test_set_navigation_shape_raises(self, pc1):
        """Desired error message."""
        detector = EBSDDetector(pc=pc1)
        with pytest.raises(ValueError, match="A maximum dimension of 2"):
            detector.navigation_shape = (1, 2, 3)

    @pytest.mark.parametrize(
        "shape, desired_x_range, desired_y_range",
        [
            ((60, 60), [-0.833828, 1.1467617], [-0.4369182, 1.54367201]),
            ((510, 510), [-0.833828, 1.1467617], [-0.4369182, 1.54367201]),
            ((1, 1), [-0.833828, 1.1467617], [-0.4369182, 1.54367201]),
            ((480, 640), [-0.6253713, 0.860071], [-0.4369182, 1.54367201]),
        ],
    )
    def test_gnomonic_range(self, pc1, shape, desired_x_range, desired_y_range):
        """Gnomonic x/y range, x depends on aspect ratio."""
        detector = EBSDDetector(shape=shape, pc=pc1)
        assert np.allclose(detector.x_range, desired_x_range)
        assert np.allclose(detector.y_range, desired_y_range)

    @pytest.mark.parametrize(
        "shape, desired_x_scale, desired_y_scale",
        [
            ((60, 60), 0.033569, 0.033569),
            ((510, 510), 0.003891, 0.003891),
            ((1, 1), 1.980590, 1.980590),
            ((480, 640), 0.002324, 0.004134),
        ],
    )
    def test_gnomonic_scale(self, pc1, shape, desired_x_scale, desired_y_scale):
        """Gnomonic x/y scale."""
        detector = EBSDDetector(shape=shape, pc=pc1)
        assert np.allclose(detector.x_scale, desired_x_scale, atol=1e-6)
        assert np.allclose(detector.y_scale, desired_y_scale, atol=1e-6)

    @pytest.mark.parametrize(
        "pc, convention, desired_pc",
        [
            ([0.421, 0.2206, 0.5049], "tsl", [0.421, 0.7794, 0.5049]),
            ([0.421, 0.2206, 0.5049], "oxford", [0.421, 0.7794, 0.5049]),
            ([0.421, 0.7794, 0.5049], "bruker", [0.421, 0.7794, 0.5049]),
            ([0.421, 0.7794, 0.5049], None, [0.421, 0.7794, 0.5049]),
            ([-37.92, -134.112, 16964.64], "emsoft", [0.421, 0.7794, 0.5049]),
        ],
    )
    def test_set_pc_convention(self, pc, convention, desired_pc):
        """PC is converted to Bruker's format via correct conversion."""
        detector = EBSDDetector(
            shape=(480, 480), px_size=70, pc=pc, convention=convention
        )
        assert np.allclose(detector.pc, desired_pc)
        assert np.allclose(detector.to_tsl(), [0.421, 0.2206, 0.5049])


#        assert np.allclose(detector.to_emsoft(), [-37.92, -134.112, 16964.64])
