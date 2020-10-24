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

from kikuchipy import data
from kikuchipy.signals import (
    EBSD,
    LazyEBSD,
    EBSDMasterPattern,
    LazyEBSDMasterPattern,
)


class TestData:
    def test_load_nickel_ebsd(self):
        s = data.nickel_ebsd()

        assert isinstance(s, EBSD)
        assert s.data.shape == (3, 3, 60, 60)

        s2 = data.nickel_ebsd(lazy=True)

        assert isinstance(s2, LazyEBSD)

    def test_load_nickel_master_pattern(self):
        smp = data.nickel_master_pattern()

        assert isinstance(smp, EBSDMasterPattern)
        assert smp.data.shape == (701, 701)

        smp2 = data.nickel_master_pattern(lazy=True)

        assert isinstance(smp2, LazyEBSDMasterPattern)
