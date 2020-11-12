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

from typing import Optional, Union, List

import dask.array as da
from hyperspy._signals.signal2d import Signal2D
from hyperspy._lazy_signals import LazySignal2D
from hyperspy.misc.utils import DictionaryTreeBrowser
import numpy as np
from orix.vector import Vector3d
from orix.quaternion import Rotation

from kikuchipy.detectors.ebsd_detector import EBSDDetector
from kikuchipy.pattern import rescale_intensity
from kikuchipy.projections.lambert_projection import LambertProjection
from kikuchipy.signals import LazyEBSD
from kikuchipy.signals.util._metadata import (
    ebsd_master_pattern_metadata,
    metadata_nodes,
    _update_phase_info,
    _write_parameters_to_dictionary,
)
from kikuchipy.signals._common_image import CommonImage


class EBSDMasterPattern(CommonImage, Signal2D):
    """Simulated Electron Backscatter Diffraction (EBSD) master pattern.

    This class extends HyperSpy's Signal2D class for EBSD master
    patterns.

    Methods inherited from HyperSpy can be found in the HyperSpy user
    guide.

    See the docstring of :class:`hyperspy.signal.BaseSignal` for a list
    of attributes.

    """

    _signal_type = "EBSDMasterPattern"
    _alias_signal_types = ["ebsd_master_pattern", "master_pattern"]
    _lazy = False

    def __init__(self, *args, **kwargs):
        """Create an :class:`~kikuchipy.signals.EBSDMasterPattern`
        object from a :class:`hyperspy.signals.Signal2D` or a
        :class:`numpy.ndarray`.

        """

        Signal2D.__init__(self, *args, **kwargs)

        # Update metadata if object is initialized from numpy array or
        # with set_signal_type()
        if not self.metadata.has_item(metadata_nodes("ebsd_master_pattern")):
            md = self.metadata.as_dictionary()
            md.update(ebsd_master_pattern_metadata().as_dictionary())
            self.metadata = DictionaryTreeBrowser(md)
        if not self.metadata.has_item("Sample.Phases"):
            self.set_phase_parameters()

    def set_simulation_parameters(
        self,
        complete_cutoff: Union[None, int, float] = None,
        depth_step: Union[None, int, float] = None,
        energy_step: Union[None, int, float] = None,
        hemisphere: Union[None, str] = None,
        incident_beam_energy: Union[None, int, float] = None,
        max_depth: Union[None, int, float] = None,
        min_beam_energy: Union[None, int, float] = None,
        mode: Optional[str] = None,
        number_of_electrons: Optional[int] = None,
        pixels_along_x: Optional[int] = None,
        projection: Union[None, str] = None,
        sample_tilt: Union[None, int, float] = None,
        smallest_interplanar_spacing: Union[None, int, float] = None,
        strong_beam_cutoff: Union[None, int, float] = None,
        weak_beam_cutoff: Union[None, int, float] = None,
    ):
        """Set simulated parameters in signal metadata.

        Parameters
        ----------
        complete_cutoff
            Bethe parameter c3.
        depth_step
            Material penetration depth step size, in nm.
        energy_step
            Energy bin size, in keV.
        hemisphere
            Which hemisphere(s) the data contains.
        incident_beam_energy
            Incident beam energy, in keV.
        max_depth
            Maximum material penetration depth, in nm.
        min_beam_energy
            Minimum electron energy to consider, in keV.
        mode
            Simulation mode, e.g. Continuous slowing down
            approximation (CSDA) used by EMsoft.
        number_of_electrons
            Total number of incident electrons.
        pixels_along_x
            Pixels along horizontal direction.
        projection
            Which projection the pattern is in.
        sample_tilt
            Sample tilte angle from horizontal, in degrees.
        smallest_interplanar_spacing
            Smallest interplanar spacing, d-spacing, taken into account
            in the computation of the electrostatic lattice potential,
            in nm.
        strong_beam_cutoff
            Bethe parameter c1.
        weak_beam_cutoff
            Bethe parameter c2.

        See Also
        --------
        set_phase_parameters

        Examples
        --------
        >>> import kikuchipy as kp
        >>> ebsd_mp_node = kp.signals.util.metadata_nodes(
        ...     "ebsd_master_pattern")
        >>> s.metadata.get_item(ebsd_mp_node + '.incident_beam_energy')
        15.0
        >>> s.set_simulated_parameters(incident_beam_energy=20.5)
        >>> s.metadata.get_item(ebsd_mp_node + '.incident_beam_energy')
        20.5
        """
        md = self.metadata
        ebsd_mp_node = metadata_nodes("ebsd_master_pattern")
        _write_parameters_to_dictionary(
            {
                "BSE_simulation": {
                    "depth_step": depth_step,
                    "energy_step": energy_step,
                    "incident_beam_energy": incident_beam_energy,
                    "max_depth": max_depth,
                    "min_beam_energy": min_beam_energy,
                    "mode": mode,
                    "number_of_electrons": number_of_electrons,
                    "pixels_along_x": pixels_along_x,
                    "sample_tilt": sample_tilt,
                },
                "Master_pattern": {
                    "Bethe_parameters": {
                        "complete_cutoff": complete_cutoff,
                        "strong_beam_cutoff": strong_beam_cutoff,
                        "weak_beam_cutoff": weak_beam_cutoff,
                    },
                    "smallest_interplanar_spacing": smallest_interplanar_spacing,
                    "projection": projection,
                    "hemisphere": hemisphere,
                },
            },
            md,
            ebsd_mp_node,
        )

    def set_phase_parameters(
        self,
        number: int = 1,
        atom_coordinates: Optional[dict] = None,
        formula: Optional[str] = None,
        info: Optional[str] = None,
        lattice_constants: Union[
            None, np.ndarray, List[float], List[int]
        ] = None,
        laue_group: Optional[str] = None,
        material_name: Optional[str] = None,
        point_group: Optional[str] = None,
        setting: Optional[int] = None,
        source: Optional[str] = None,
        space_group: Optional[int] = None,
        symmetry: Optional[int] = None,
    ):
        """Set parameters for one phase in signal metadata.

        A phase node with default values is created if none is present
        in the metadata when this method is called.

        Parameters
        ----------
        number
            Phase number.
        atom_coordinates
            Dictionary of dictionaries with one or more of the atoms in
            the unit cell, on the form `{'1': {'atom': 'Ni',
            'coordinates': [0, 0, 0], 'site_occupation': 1,
            'debye_waller_factor': 0}, '2': {'atom': 'O',... etc.`
            `debye_waller_factor` in units of nm^2, and
            `site_occupation` in range [0, 1].
        formula
            Phase formula, e.g. 'Fe2' or 'Ni'.
        info
            Whatever phase info the user finds relevant.
        lattice_constants
            Six lattice constants a, b, c, alpha, beta, gamma.
        laue_group
            Phase Laue group.
        material_name
            Name of material.
        point_group
            Phase point group.
        setting
            Space group's origin setting.
        source
            Literature reference for phase data.
        space_group
            Number between 1 and 230.
        symmetry
            Phase symmetry.

        See Also
        --------
        set_simulation_parameters

        Examples
        --------
        >>> s.metadata.Sample.Phases.Number_1.atom_coordinates.Number_1
        ├── atom =
        ├── coordinates = array([0., 0., 0.])
        ├── debye_waller_factor = 0.0
        └── site_occupation = 0.0
        >>> s.set_phase_parameters(
        ...     number=1, atom_coordinates={
        ...         '1': {'atom': 'Ni', 'coordinates': [0, 0, 0],
        ...         'site_occupation': 1,
        ...         'debye_waller_factor': 0.0035}})
        >>> s.metadata.Sample.Phases.Number_1.atom_coordinates.Number_1
        ├── atom = Ni
        ├── coordinates = array([0., 0., 0.])
        ├── debye_waller_factor = 0.0035
        └── site_occupation = 1
        """
        # Ensure atom coordinates are numpy arrays
        if atom_coordinates is not None:
            for phase, val in atom_coordinates.items():
                atom_coordinates[phase]["coordinates"] = np.array(
                    atom_coordinates[phase]["coordinates"]
                )

        inputs = {
            "atom_coordinates": atom_coordinates,
            "formula": formula,
            "info": info,
            "lattice_constants": lattice_constants,
            "laue_group": laue_group,
            "material_name": material_name,
            "point_group": point_group,
            "setting": setting,
            "source": source,
            "space_group": space_group,
            "symmetry": symmetry,
        }

        # Remove None values
        phase = {k: v for k, v in inputs.items() if v is not None}
        _update_phase_info(self.metadata, phase, number)

    def get_patterns(
        self,
        rotations: Rotation,
        detector: EBSDDetector,
        energy: int,
        n_chunk=-1,
        dtype_out=np.float32,
    ) -> LazyEBSD:
        """
        Creates a dictionary of EBSD patterns for a sample in the
        (RD, TD, ND) reference frame, given a set of local crystal lattice
        rotations and a detector model from a master pattern in the Lambert
        projection.

        Parameters
        ----------
        rotations : Rotation
            Set of unit cell rotations to get patterns from.
        detector : EBSDDetector
            EBSDDetector object describing the detector geometry with one
            projection center.
        energy : int
            The wanted energy in the master pattern.
        n_chunk : int, optional
            The number of chunks the data should be split up into. By default,
            this is set so each chunk is around 100 MB.
        dtype_out : numpy.dtype, optional
            Data type of the returned patterns, by default np.float32.

        Returns
        ----------
        LazyEBSD object containing the simulated EBSD patterns with the shape
        (number of rotations, detector pixels in x direction, detector pixels
        in y direction).

        Notes
        ----------
        If the master pattern phase has a non-centrosymmetric point group, both
        the northern and southern hemispheres must be provided to yield the
        correct result.
        For more details regarding the reference frame visit the reference frame
        user guide at kikuchipy.org/en/latest/reference_frames.html.
        """

        if (
            self.metadata.Simulation.EBSD_master_pattern.Master_pattern.projection
            != "lambert"
        ):
            raise NotImplementedError(
                "Method only supports master patterns in lambert projection!"
            )
        pc = detector.pc_emsoft()
        if len(pc) > 1:
            raise ValueError("Method only supports a single projection center!")

        dc = _get_direction_cosines(detector)

        n = rotations.size
        det_y, det_x = detector.shape
        dtype_out = dtype_out

        if n_chunk == -1:
            n_chunk = _min_number_of_chunks(detector, rotations, dtype_out)

        out_shape = (n, det_y, det_x)
        chunks = (int(np.ceil(n / n_chunk)), det_y, det_x)

        rescale = False
        if dtype_out != np.float32:
            rescale = True

        r_da = da.from_array(rotations.data, chunks=(chunks[0], -1))

        # 4 cases
        # Has energies, has hemis - Case 1
        if len(self.axes_manager.shape) == 4:
            energies = self.axes_manager["energy"].axis
            energy_index = (np.abs(energies - energy)).argmin()
            mpn = self.data[0, energy_index]
            mps = self.data[1, energy_index]

        # no energies, no hemis - Case 2
        elif len(self.axes_manager.shape) == 2:
            mpn = self.data
            mps = mpn
        else:
            try:  # has energies, no hemi - Case 3
                # TODO: Raise warning if not centro and no hemi
                energies = self.axes_manager["energy"].axis
                energy_index = (np.abs(energies - energy)).argmin()
                mpn = self.data[energy_index]
                mps = mpn
            except ValueError:  # no energies, yes hemi - Case 4
                mpn = self.data[0]
                mps = self.data[1]

        npx, npy = self.axes_manager.signal_shape

        simulated = r_da.map_blocks(
            _get_patterns_chunk,
            dc=dc,
            master_north=mpn,
            master_south=mps,
            npx=npx,
            npy=npy,
            rescale=rescale,
            dtype_out=dtype_out,
            drop_axis=1,
            new_axis=(1, 2),
            chunks=chunks,
            dtype=dtype_out,
        )

        names = ["x", "dy", "dx"]
        scales = np.ones(3)

        # Create axis objects for each axis
        axes = [
            {
                "size": out_shape[i],
                "index_in_array": i,
                "name": names[i],
                "scale": scales[i],
                "offset": 0.0,
                "units": "px",
            }
            for i in range(simulated.ndim)
        ]

        return LazyEBSD(simulated, axes=axes)


class LazyEBSDMasterPattern(EBSDMasterPattern, LazySignal2D):
    """Lazy implementation of the :class:`EBSDMasterPattern` class.

    This class extends HyperSpy's LazySignal2D class for EBSD master
    patterns.

    Methods inherited from HyperSpy can be found in the HyperSpy user
    guide.

    See docstring of :class:`EBSDMasterPattern` for attributes and
    methods.

    """

    _lazy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def _get_direction_cosines(detector: EBSDDetector) -> Vector3d:
    """
    Get the direction cosines between the detector and sample as done in EMsoft
    and [Callahan2013]_.

    Parameters
    ----------
    detector : EBSDDetector
        EBSDDetector object with a certain detector geometry.

    Returns
    ----------
    r_g.unit : Vector3d
        Vector3d object containing the direction cosines for each detector
        pixel.
    """

    pc = detector.pc_emsoft()
    xpc = pc[..., 0]
    ypc = pc[..., 1]
    L = pc[..., 2]

    # Detector coordinates in microns
    det_x = (
        -((-xpc - (1.0 - detector.ncols) * 0.5) - np.arange(0, detector.ncols))
        * detector.px_size
    )
    det_y = (
        (ypc - (1.0 - detector.nrows) * 0.5) - np.arange(0, detector.nrows)
    ) * detector.px_size

    # Auxilliary angle to rotate between reference frames
    theta_c = np.radians(detector.tilt)
    sigma = np.radians(detector.sample_tilt)

    alpha = (np.pi / 2) - sigma + theta_c
    ca = np.cos(alpha)
    sa = np.sin(alpha)

    # NYI
    omega = np.radians(0)  # angle between normal of sample and detector
    cw = np.cos(omega)
    sw = np.sin(omega)

    r_g_array = np.zeros((detector.nrows, detector.ncols, 3))

    Ls = -sw * det_x + L * cw
    Lc = cw * det_x + L * sw

    i, j = np.meshgrid(
        np.arange(detector.nrows - 1, -1, -1),
        np.arange(detector.ncols),
        indexing="ij",
    )

    r_g_array[..., 0] = det_y[i] * ca + sa * Ls[j]
    r_g_array[..., 1] = Lc[j]
    r_g_array[..., 2] = -sa * det_y[i] + ca * Ls[j]
    r_g = Vector3d(r_g_array)

    return r_g.unit


def _get_lambert_interpolation_parameters(
    rotated_direction_cosines: Vector3d,
    scale: Union[int, float],
    npx: int,
    npy: int,
) -> tuple:
    """Get Lambert interpolation parameters as described in EMsoft.

    Parameters
    ----------
    rotated_direction_cosines : Vector3d
        Rotated direction cosines vector.
    scale : int
        Factor to scale up from Rosca-Lambert projection to the master pattern.
    npx : int
        Number of pixels on the master pattern in the x direction.
    npy : int
        Number of pixels on the master pattern in the y direction.

    Returns
    ----------
    nii : numpy.ndarray
        Row coordinate of a point.
    nij : numpy.ndarray
        Column coordinate of a point.
    niip : numpy.ndarray
        Row coordinate of neighboring point.
    nijp : numpy.ndarray
        Column coordinate of a neighboring point.
    di : numpy.ndarray
        Interpolation weight factor.
    dj : numpy.ndarray
        Interpolation weight factor.
    dim : numpy.ndarray
        Interpolation weight factor.
    djm : numpy.ndarray
        Interpolation weight factor.
    """
    # Normalized direction cosines to Rosca-Lambert projection
    xy = (
        scale
        * LambertProjection.project(rotated_direction_cosines)
        / (np.sqrt(np.pi / 2))
    )

    i = xy[..., 0]
    j = xy[..., 1]
    nii = (i + scale).astype(int)
    nij = (j + scale).astype(int)
    niip = nii + 1
    nijp = nij + 1
    niip = np.where(niip < npx, niip, nii)
    nijp = np.where(nijp < npy, nijp, nij)
    nii = np.where(nii < 0, niip, nii)
    nij = np.where(nij < 0, nijp, nij)
    di = i - nii + scale
    dj = j - nij + scale
    dim = 1.0 - di
    djm = 1.0 - dj

    return (
        nii.astype(int),
        nij.astype(int),
        niip.astype(int),
        nijp.astype(int),
        di,
        dj,
        dim,
        djm,
    )


def _get_patterns_chunk(
    r: Rotation,
    dc: Vector3d,
    master_north: np.ndarray,
    master_south: np.ndarray,
    npx: int,
    npy: int,
    rescale: bool,
    dtype_out=np.float32,
) -> np.ndarray:
    """
    Get the EBSD patterns on the detector for each rotation in the chunk.

    Each pattern is found by a bi-quadratic interpolation of the master pattern
    as described in EMsoft.

    Parameters
    ----------
    r : Rotation
        Rotation object with all the rotations for a given chunk.
    dc : Vector3d
        Direction cosines unit vector between detector and sample.
    master_north : numpy.ndarray
        Northern hemisphere of the master pattern.
    master_south : numpy.ndarray
        Southern hemisphere of the master pattern.
    npx : int
        Number of pixels in the x-direction on the master pattern.
    npy: int
        Number of pixels in the y-direction on the master pattern.
    rescale : bool
        Whether to call rescale_intensities() or not.
    dtype_out : numpy.dtype, optional
        Data type of the returned patterns, by default np.float32.

    Returns
    ----------
    simulated : numpy.ndarray
        Ndarray with shape (n, y, x) containing all the patterns.


    """
    m = r.shape[0]
    simulated = np.empty(shape=(m,) + dc.shape, dtype=dtype_out)

    scale_factor = (npx - 1) / 2

    for i in range(m):
        rot_dc = Rotation(r[i]) * dc
        (
            nii,
            nij,
            niip,
            nijp,
            di,
            dj,
            dim,
            djm,
        ) = _get_lambert_interpolation_parameters(
            rotated_direction_cosines=rot_dc,
            scale=scale_factor,
            npx=npx,
            npy=npy,
        )

        pattern = np.where(
            rot_dc.z >= 0,
            (
                master_north[nii, nij] * dim * djm
                + master_north[niip, nij] * di * djm
                + master_north[nii, nijp] * dim * dj
                + master_north[niip, nijp] * di * dj
            ),
            (
                master_south[nii, nij] * dim * djm
                + master_south[niip, nij] * di * djm
                + master_south[nii, nijp] * dim * dj
                + master_south[niip, nijp] * di * dj
            ),
        )
        if rescale:
            pattern = rescale_intensity(pattern, dtype_out=dtype_out)
        simulated[i] = pattern
    return simulated


def _min_number_of_chunks(
    d: EBSDDetector, r: Rotation, dtype_out=np.dtype
) -> int:
    """Returns the minimum number of chunks required for our detector model and
     set of unit cell rotations so that each chunk is around 100 MB.

     Parameteres
     -----------
     d : EBSDDetector
        EBSDDetector object with the detector geometry.
    r : Rotation
        Rotation object containing all the unit cell rotations.
    dtype_out : np.dtype
        The output data type.
     Returns
     ----------
     int
        The minimum number of chunks required so each chunk is around 100 MB.
    """
    dy, dx = d.shape
    n = r.size
    nbytes = dy * dx * n.astype("int64") * np.dtype(dtype_out).itemsize
    nbytes_goal = 100e6  # 100 MB
    n_chunks = int(np.ceil(nbytes / nbytes_goal))
    return n_chunks
