# -*- coding: utf-8 -*-
# Copyright 2019-2020 The KikuchiPy developers
#
# This file is part of KikuchiPy.
#
# KikuchiPy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KikuchiPy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with KikuchiPy. If not, see <http://www.gnu.org/licenses/>.

import dask.array as da
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.exposure import equalize_adapthist
from skimage.util.dtype import dtype_range


def _rescale_pattern(pattern, in_range=None, out_range=None, dtype_out=None):
    """Rescale pattern intensities inplace to desired
    :class:`numpy.dtype` range specified by ``dtype_out`` keeping
    relative intensities or not.

    This method makes use of :func:`skimage.exposure.rescale_intensity`.

    Parameters
    ----------
    pattern : dask.array.Array
        Pattern to rescale.
    in_range, out_range : tuple of int or float, optional
        Min./max. intensity values of input and output pattern. If None,
        (default) `in_range` is set to pattern min./max. If None
        (default), `out_range` is set to `dtype_out` min./max
        according to `skimage.util.dtype.dtype_range`, with min. equal
        to zero.
    dtype_out : np.dtype, optional
        Data type of rescaled pattern. If None (default), it is set to
        the same data type as the input pattern.

    Returns
    -------
    rescaled_pattern : da.Array
        Rescaled pattern.
    """

    if dtype_out is None:
        dtype_out = pattern.dtype

    if in_range is None:
        imin, imax = (pattern.min(), pattern.max())
    else:
        imin, imax = in_range
        pattern.clip(imin, imax)

    if out_range is None or out_range in dtype_range:
        omin = 0
        try:
            if isinstance(dtype_out, np.dtype):
                dtype_out = dtype_out.type
            _, omax = dtype_range[dtype_out]
        except KeyError:
            raise KeyError(
                "Could not set output intensity range, since data type "
                f"'{dtype_out}' is not recognised. Use any of '{dtype_range}'."
            )
    else:
        omin, omax = out_range

    rescaled_pattern = (pattern - imin) / float(imax - imin)
    return (rescaled_pattern * (omax - omin) + omin).astype(dtype_out)


def _rescale_pattern_chunk(
    patterns, in_range=None, out_range=None, dtype_out=None
):
    """Rescale patterns in chunk to fill the data type range using an
    approach inspired by `skimage.exposure.rescale_intensity`, keeping
    relative intensities or not.

    Parameters
    ----------
    patterns : da.Array
        Patterns to rescale.
    in_range, out_range : tuple of int or float, optional
        Min./max. intensity values of input and output pattern. If None,
        (default) `in_range` is set to pattern min./max. If None
        (default), `out_range` is set to `dtype_out` min./max
        according to `skimage.util.dtype_out.dtype_range`, with min. equal
        to zero.
    dtype_out : np.dtype, optional
        Data type of rescaled patterns. If None (default), it is set to
        the same data type as the input patterns.

    Returns
    -------
    rescaled_patterns : da.Array
        Rescaled patterns.
    """

    rescaled_patterns = np.empty_like(patterns, dtype=dtype_out)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        rescaled_patterns[nav_idx] = _rescale_pattern(
            patterns[nav_idx],
            in_range=in_range,
            out_range=out_range,
            dtype_out=dtype_out,
        )
    return rescaled_patterns


def _static_background_correction_chunk(
    patterns, static_bg, operation="subtract", in_range=None, dtype_out=None
):
    """Correct static background in patterns in chunk by subtracting or
    dividing by a static background pattern. Returned pattern
    intensities are rescaled keeping relative intensities or not and
    stretched to fill the input data type range.

    Parameters
    ----------
    patterns : da.Array
        Patterns to correct static background in.
    static_bg : np.ndarray or da.Array
        Static background pattern. If not passed we try to read it
        from the signal metadata.
    operation : 'subtract' or 'divide', optional
        Subtract (default) or divide by static background pattern.
    in_range : tuple of int or float, optional
        Min./max. intensity values of input and output patterns. If
        None, (default) `in_range` is set to pattern min./max, losing
        relative intensities between patterns.
    dtype_out : np.dtype, optional
        Data type of corrected patterns. If None (default), it is set to
        the same data type as the input patterns.

    Returns
    -------
    corrected_patterns : da.Array
        Static background corrected patterns.
    """

    if dtype_out is None:
        dtype_out = patterns.dtype

    corrected_patterns = np.empty_like(patterns, dtype=dtype_out)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        if operation == "subtract":
            corrected_pattern = patterns[nav_idx] - static_bg
        else:  # Divide
            corrected_pattern = patterns[nav_idx] / static_bg
        corrected_patterns[nav_idx] = _rescale_pattern(
            corrected_pattern, in_range=in_range, dtype_out=dtype_out
        )

    return corrected_patterns


def _dynamic_background_correction_chunk(
    patterns, sigma, operation="subtract", dtype_out=None
):
    """Correct dynamic background in chunk of patterns by subtracting
    or dividing by a blurred version of each pattern.

    Returned pattern intensities are stretched to fill the input data
    type range.

    Parameters
    ----------
    patterns : dask.array.Array
        Patterns to correct dynamic background in.
    sigma : int, float or None
        Standard deviation of the gaussian kernel.
    operation : 'subtract' or 'divide', optional
        Subtract (default) or divide by dynamic background pattern.
    dtype_out : numpy.dtype, optional
        Data type of corrected patterns. If ``None`` (default), it is
        set to the same data type as the input patterns.

    Returns
    -------
    corrected_patterns : dask.array.Array
        Dynamic background corrected patterns.
    """

    if dtype_out is None:
        dtype_out = patterns.dtype

    corrected_patterns = np.empty_like(patterns, dtype=dtype_out)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        pattern = patterns[nav_idx]
        blurred = gaussian_filter(pattern, sigma=sigma)
        if operation == "subtract":
            corrected_pattern = pattern - blurred
        else:  # Divide
            corrected_pattern = pattern / blurred
        corrected_patterns[nav_idx] = _rescale_pattern(
            corrected_pattern, dtype_out=dtype_out,
        )

    return corrected_patterns


def _adaptive_histogram_equalization_chunk(
    patterns, kernel_size, clip_limit=0, nbins=128
):
    """Local contrast enhancement on chunk of patterns with adaptive
    histogram equalization.

    This method makes use of
    :func:`skimage.exposure.equalize_adapthist`.


    Parameters
    ----------
    patterns : dask.array.Array
        Patterns to enhance.
    kernel_size : int or list-like
        Shape of contextual regions for adaptive histogram equalization.
    clip_limit : float, optional
        Clipping limit, normalized between 0 and 1 (higher values give
        more contrast). Default is 0.
    nbins : int, optional
        Number of gray bins for histogram ("data range"), default is
        128.

    Returns
    -------
    equalized_patterns : dask.array.Array
        Patterns with enhanced contrast.
    """

    dtype_in = patterns.dtype.type
    equalized_patterns = np.empty_like(patterns)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        equalized_pattern = equalize_adapthist(
            patterns[nav_idx],
            kernel_size=kernel_size,
            clip_limit=clip_limit,
            nbins=nbins,
        )
        equalized_patterns[nav_idx] = _rescale_pattern(
            equalized_pattern, dtype_out=dtype_in
        )
    return equalized_patterns


def _image_quality_map(
    patterns,
    frequency_vectors,
    inertia_max,
    normalize,
    divide_square_root,
    method,
    dtype_out=None,
):
    if dtype_out is None:
        dtype_out = patterns.dtype
    image_quality_map_chunk = np.empty(patterns.shape[:-2], dtype=dtype_out)

    for nav_idx in np.ndindex(patterns.shape[:-2]):
        pattern = patterns[nav_idx]

        if normalize:
            # Normalize pattern
            pattern = _normalize_pattern(
                pattern, divide_square_root=divide_square_root
            )

        # Get FFT spectrum
        spectrum = _fft_spectrum_pattern(pattern, method)

        # Get image quality
        inertia = np.sum(spectrum * frequency_vectors) / np.sum(spectrum)
        image_quality_map_chunk[nav_idx] = 1 - (inertia / inertia_max)

    return image_quality_map_chunk


def _frequency_vectors(signal_shape, method):
    sx, sy = signal_shape
    if method == 1:
        linex = np.arange(sx)
        linex[sx // 2 + 1 : sx] -= sx
        liney = np.arange(sy)
        liney[sy // 2 + 1 : sy] -= sy
    else:
        linex = np.arange(-sx // 2, sx // 2)
        liney = np.arange(-sy // 2, sy // 2)

    frequency_vectors = np.empty(shape=(sy, sx))
    for i in range(sx):
        frequency_vectors[i] = linex[i] ** 2 + liney ** 2

    return frequency_vectors


def _fft_spectrum_pattern(pattern, method):
    fft_pattern = np.fft.fft2(pattern)
    if method == 1:
        fft_shifted = fft_pattern
    else:
        fft_shifted = np.fft.fftshift(fft_pattern)
    fft_spectrum = np.sqrt(fft_shifted.real ** 2 + fft_shifted.imag ** 2)
    return fft_spectrum


def _fft_spectrum_chunk(
    patterns, dtype_out=None, normalize=False, divide_square_root=False
):
    if dtype_out is None:
        dtype_out = patterns.dtype
    fft_spectra = np.empty_like(patterns, dtype=dtype_out)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        pattern = patterns[nav_idx]
        if normalize:
            pattern = _normalize_pattern(
                pattern, divide_square_root=divide_square_root
            )
        fft_spectra[nav_idx] = _fft_spectrum_pattern(pattern)
    return fft_spectra


def _normalize_pattern_chunk(
    patterns, num_std=1, divide_square_root=False, dtype_out=None
):
    if dtype_out is None:
        dtype_out = patterns.dtype
    normalized_patterns = np.empty_like(patterns, dtype=dtype_out)
    for nav_idx in np.ndindex(patterns.shape[:-2]):
        normalized_patterns[nav_idx] = _normalize_pattern(
            pattern=patterns[nav_idx],
            num_std=num_std,
            divide_square_root=divide_square_root,
        )
    return normalized_patterns


def _normalize_pattern(pattern, num_std=1, divide_square_root=False):
    pattern_mean = np.mean(pattern)
    pattern_std = np.std(pattern)
    normalized_pattern = (pattern - pattern_mean) / (num_std * pattern_std)
    if divide_square_root:
        normalized_pattern = normalized_pattern / np.sqrt(pattern.size)
    return normalized_pattern


def normalised_correlation_coefficient(pattern, template, zero_normalised=True):
    """Calculate the normalised or zero-normalised correlation
    coefficient between a pattern and a template following
    [Gonzalez2008]_.

    Parameters
    ----------
    pattern : numpy.ndarray or dask.array.Array
        Pattern to compare the template to.
    template : numpy.ndarray or dask.array.Array
        Template pattern.
    zero_normalised : bool, optional
        Subtract local mean value of intensities (default is ``True``).

    Returns
    -------
    coefficient : float
        Correlation coefficient in range [-1, 1] if zero normalised,
        otherwise [0, 1].

    References
    ----------
    .. [Gonzalez2008] Gonzalez, Rafael C, Woods, Richard E: Digital\
        Image Processing, 3rd edition, Pearson Education, 954, 2008.
    """

    pattern = pattern.astype(np.float32)
    template = template.astype(np.float32)
    if zero_normalised:
        pattern = pattern - pattern.mean()
        template = template - template.mean()
    coefficient = np.sum(pattern * template) / np.sqrt(
        np.sum(pattern ** 2) * np.sum(template ** 2)
    )
    return coefficient
