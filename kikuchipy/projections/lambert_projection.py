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

from typing import Union
import numpy as np
from orix.vector import Vector3d
# These may not be needed?
# from kikuchipy.projections.gnomonic_projection import GnomonicProjection
from kikuchipy.projections.spherical_projection import SphericalProjection

# Temporary notes for myself :)
# Bunge Euler triplets
# phi1, Phi, phi2

# Pattern center
# 2D coordinates = xpc, ypc

# All coordinates in units of micrometers


class LambertProjection(SphericalProjection):
    """Lambert Projection of a vector (as implemented in MTEX?)"""

    def project(self, v: Union[Vector3d, np.ndarray]) -> np.ndarray:

        if isinstance(v, Vector3d):
            x = v.x
            y = v.y
            z = v.z
        else:
            x = v[..., 0]
            y = v[..., 1]
            z = v[..., 2]

        # TODO: Implement requirement checker for which equation to use
        something_important = True # Very temporary :)
        if something_important:
            # Equation 10a - Requirement: |y| <= |x|
            X = np.sign(x)*np.sqrt(2*(1-z))*((np.sqrt(np.pi))/2)
            Y = np.sign(x)*np.sqrt(2*(1-z))*((2/(np.sqrt(np.pi))) * np.arctan(y/x))
        else:
            # Equation 10b - Requirement: |x| <= |y|
            X = np.sign(y)*np.sqrt(2*(1-z))*((2/(np.sqrt(np.pi))) * np.arctan(x/y))
            Y = np.sign(y)*np.sqrt(2*(1-z))*((np.sqrt(np.pi))/2)

        return np.column_stack((X, Y))

    @staticmethod
    def iproject(x: np.ndarray, y: np.ndarray) -> Vector3d:
        X = x  # v[..., 0] The user needs to input this array?
        Y = y  # v[..., 1] The user needs to input this array?
        # A perhaps easier solution would be to take in **ONE** np.ndarray v and set X = v[..., 0], Y = v[..., 1]?
        # TODO: Implement requirement checker for which equation to use
        something_important_again = True # Very temporary :)
        if something_important_again:
            # 0 < |Y| <= |X| <= L
            x = eq_c(X)*np.cos((Y*np.pi)/(4*X))
            y = eq_c(X)*np.sin((Y*np.pi)/(4*X))
            z = 1 - (2*(X**2))/np.pi
        else:
            # 0 < |X| <= |X| <= L
            x = eq_c(Y)*np.sin((X*np.pi)/(4*Y))
            y = eq_c(Y)*np.cos((X*np.pi)/(4*Y))
            z = 1 - (2*(Y**2))/np.pi

        v = np.column_stack((x, y, z))

        return Vector3d(v)


def eq_c(p: np.darray) -> np.ndarray:
    return 2/(np.pi) * np.sqrt(np.pi - p**2)


# TODO: Create Lambert to Gnomonic method
def lambert_to_gnomonic(v: np.ndarray) -> np.ndarray:
    pass

# TODO: Create Gnomonic to Lambert method
def gnomonic_to_lambert(v: np.ndarray) -> np.ndarray:
    pass

