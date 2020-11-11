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

from typing import Union, List

import numpy as np
from orix.crystal_map import CrystalMap

from kikuchipy.indexing._merge_crystal_maps import merge_crystal_maps
from kikuchipy.indexing.orientation_similarity_map import (
    orientation_similarity_map,
)
from kikuchipy.indexing._pattern_matching import _pattern_match
from kikuchipy.indexing.similarity_metrics import (
    SimilarityMetric,
    _SIMILARITY_METRICS,
)


class StaticDictionaryIndexing:
    """Dictionary indexing :cite:`chen2015dictionary` by comparing
    experimental EBSD patterns against dictionaries of pre-computed
    simulated patterns.
    """

    def __init__(self, dictionaries):
        """Set up dictionary indexing with one or more dictionaries of
        pre-computed simulated patterns.

        Parameters
        ----------
        dictionaries : EBSD or list of EBSD
            Dictionaries as EBSD signals with a 1D navigation axis and
            the `xmap` property with crystal orientations set.
        """
        if not isinstance(dictionaries, list):
            dictionaries = [dictionaries]
        self.dictionaries = dictionaries

    def __call__(
        self,
        signal,
        metric: Union[str, SimilarityMetric] = "ncc",
        keep_n: int = 50,
        n_slices: int = 1,
        return_merged_crystal_map: bool = False,
        get_orientation_similarity_map: bool = False,
    ) -> Union[CrystalMap, List[CrystalMap]]:
        """Perform dictionary indexing :cite:`chen2015dictionary` by
        comparing experimental patterns against pre-computed simulations
        with normalized cross-correlation or a user-defined similarity
        metric.

        :class:`~orix.crystal_map.crystal_map.CrystalMap`'s for each
        dictionary with "scores" and "simulation_indices" as properties
        are returned.

        Parameters
        ----------
        signal : EBSD
            EBSD signal with experimental patterns.
        metric : str or SimilarityMetric, optional
            Similarity metric, by default "ncc" (normalized
            cross-correlation).
        keep_n : int, optional
            Number of best matches to keep, by default 50 or the number
            of simulated patterns if fewer than 50 are available.
        n_slices : int, optional
            Number of simulation slices to process sequentially, by
            default 1 (no slicing).
        return_merged_crystal_map : bool, optional
            Whether to return a merged crystal map, the best matches
            determined from the similarity scores, in addition to the
            single phase maps. By default False.
        get_orientation_similarity_map : bool, optional
            Add orientation similarity maps to the returned crystal
            maps' properties named "osm". By default False.

        Returns
        -------
        xmaps : :class:`~orix.crystal_map.crystal_map.CrystalMap` or \
                list of \
                :class:`~orix.crystal_map.crystal_map.CrystalMap`
            A crystal map for each dictionary loaded and one merged map
            if `return_merged_crystal_map = True`.

        Notes
        -----
        Merging of crystal maps and calculations of orientation
        similarity maps can be done afterwards with
        :func:`~kikuchipy.indexing.merge_crystal_maps` and
        :func:`~kikuchipy.indexing.orientation_similarity_map`,
        respectively.
        """
        # This needs a rework before sent to cluster and possibly more
        # automatic slicing with dask
        n_simulations = max(
            [d.axes_manager.navigation_size for d in self.dictionaries]
        )
        good_number = 13500
        if (n_simulations // n_slices) > good_number:
            answer = input(
                "You should probably increase n_slices depending on your "
                f"available memory, try above {n_simulations // good_number}."
                " Do you want to proceed? [y/n]"
            )
            if answer != "y":
                return

        # Get metric from optimized metrics if it is available, or
        # return the metric if it is not
        metric = _SIMILARITY_METRICS.get(metric, metric)

        axes_manager = signal.axes_manager
        spatial_arrays = _get_spatial_arrays(
            shape=axes_manager.navigation_shape,
            extent=axes_manager.navigation_extent,
            step_sizes=[i.scale for i in axes_manager.navigation_axes],
        )
        n_nav_dims = axes_manager.navigation_dimension
        if n_nav_dims == 0:
            xmap_kwargs = dict()
        elif n_nav_dims == 1:
            scan_unit = axes_manager.navigation_axes[0].units
            xmap_kwargs = dict(x=spatial_arrays, scan_unit=scan_unit)
        else:  # 2d
            scan_unit = axes_manager.navigation_axes[0].units
            xmap_kwargs = dict(
                x=spatial_arrays[0], y=spatial_arrays[1], scan_unit=scan_unit,
            )

        keep_n = min([keep_n] + [d.xmap.size for d in self.dictionaries])

        # Naively let dask compute them seperately, should try in the
        # future combined compute for better performance
        xmaps = []
        patterns = signal.data
        for dictionary in self.dictionaries:
            simulation_indices, scores = _pattern_match(
                patterns,
                dictionary.data,
                metric=metric,
                keep_n=keep_n,
                n_slices=n_slices,
            )
            new_xmap = CrystalMap(
                rotations=dictionary.xmap.rotations[simulation_indices],
                phase_list=dictionary.xmap.phases_in_data,
                prop={
                    "scores": scores,
                    "simulation_indices": simulation_indices,
                },
                **xmap_kwargs,
            )
            xmaps.append(new_xmap)

        # Create a merged CrystalMap using best metric result across all
        # dictionaries
        if return_merged_crystal_map and len(self.dictionaries) > 1:
            xmap_merged = merge_crystal_maps(xmaps, metric=metric)
            xmaps.append(xmap_merged)

        # Compute orientation similarity map
        if get_orientation_similarity_map:
            for xmap in xmaps:
                osm = orientation_similarity_map(xmap, n_best=keep_n)
                xmap.prop["osm"] = osm.flatten()

        if len(xmaps) == 1:
            xmaps = xmaps[0]

        return xmaps


def _get_spatial_arrays(
    shape: tuple, extent: tuple, step_sizes: tuple
) -> Union[tuple, np.ndarray]:
    n_nav_dims = len(shape)
    if n_nav_dims == 0:
        return ()
    if n_nav_dims == 1:
        x0, x1 = extent
        dx = step_sizes[0]
        return np.arange(x0, x1 + dx, dx)
    else:
        x0, x1, y0, y1 = extent
        dx, dy = step_sizes
        x = np.tile(np.arange(x0, x1 + dx, dx), shape[1])
        y = np.tile(np.arange(y0, y1 + dy, dy), shape[0])
        return x, y
