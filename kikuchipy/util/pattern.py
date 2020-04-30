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

"""
Single EBSD pattern processing.

This module mainly includes functions operating on single EBSD patterns
as :class:`numpy.ndarray`.
"""

from typing import Union, Tuple, Optional, List

from numba import njit
import numpy as np
import scipy.fft
from scipy.ndimage import gaussian_filter
from skimage.util.dtype import dtype_range

from .barnes_fftfilter import _fft_filter, _fft_filter_setup
from .window import Window


def rescale_intensity(
    pattern: np.ndarray,
    in_range: Optional[Tuple[int, float]] = None,
    out_range: Optional[Tuple[int, float]] = None,
    dtype_out: Optional[np.dtype] = None,
) -> np.ndarray:
    """Rescale intensities in an EBSD pattern.

    Pattern max./min. intensity is determined from the data type range
    of :class:`numpy.dtype` passed to `dtype_out`.

    This method is based on :func:`skimage.exposure.rescale_intensity`.

    Parameters
    ----------
    pattern
        EBSD pattern.
    in_range, out_range
        Min./max. intensity values of input and output pattern. If None,
        (default) `in_range` is set to image min./max. If None
        (default), `out_range` is set to `dtype_out` min./max according
        to :func:`skimage.util.dtype.dtype_range`, with min. equal to
        zero.
    dtype_out
        Data type of rescaled pattern. If None (default), it is set to
        the same data type as the input pattern.

    Returns
    -------
    rescaled_pattern
        Rescaled pattern.

    """

    if dtype_out is None:
        dtype_out = pattern.dtype.type

    if in_range is None:
        imin, imax = np.min(pattern), np.max(pattern)
    else:
        imin, imax = in_range
        pattern = np.clip(pattern, imin, imax)

    if out_range is None or out_range in dtype_range:
        try:
            omin, omax = (0, dtype_range[dtype_out][-1])
        except KeyError:
            raise KeyError(
                "Could not set output intensity range, since data type "
                f"'{dtype_out}' is not recognised. Use any of '{dtype_range}'."
            )
    else:
        omin, omax = out_range

    return _rescale(pattern, imin, imax, omin, omax).astype(dtype_out)


@njit
def _rescale(
    pattern: np.ndarray,
    imin: Union[int, float],
    imax: Union[int, float],
    omin: Union[int, float],
    omax: Union[int, float],
) -> np.ndarray:
    rescaled_pattern = (pattern - imin) / float(imax - imin)
    return rescaled_pattern * (omax - omin) + omin


def remove_dynamic_background(
    pattern: np.ndarray,
    operation: str = "subtract",
    filter_domain: str = "frequency",
    std: Union[None, int, float] = None,
    truncate: Union[int, float] = 4.0,
    dtype_out: Optional[np.dtype] = None,
) -> np.ndarray:
    """Remove the dynamic background in an EBSD pattern.

    The removal is performed by subtracting or dividing by a Gaussian
    blurred version of the pattern. The blurred version is obtained
    either in the frequency domain, by a low pass Fast Fourier Transform
    (FFT) Gaussian filter, or in the spatial domain by a Gaussian
    filter. Returned pattern intensities are rescaled to fill the input
    data type range.

    Parameters
    ----------
    pattern
        EBSD pattern.
    operation
        Whether to "subtract" (default) or "divide" by the dynamic
        background pattern.
    filter_domain
        Whether to obtain the dynamic background by applying a Gaussian
        convolution filter in the "frequency" (default) or "spatial"
        domain.
    std
        Standard deviation of the Gaussian window. If None (default), it
        is set to width/8.
    truncate
        Truncate the Gaussian window at this many standard deviations.
        Default is 4.0.
    dtype_out
        Data type of corrected pattern. If None (default), it is set to
        input patterns' data type.

    Returns
    -------
    corrected_pattern
        Pattern with the dynamic background removed.

    See Also
    --------
    kikuchipy.signals.ebsd.EBSD.remove_dynamic_background
    kikuchipy.util.chunk.remove_dynamic_background

    """

    if std is None:
        std = pattern.shape[1] / 8

    if dtype_out is None:
        dtype_out = pattern.dtype.type

    if filter_domain == "frequency":
        (
            fft_shape,
            kernel_shape,
            kernel_fft,
            offset_before_fft,
            offset_after_ifft,
        ) = _dynamic_background_frequency_space_setup(
            pattern_shape=pattern.shape, std=std, truncate=truncate,
        )
        dynamic_bg = _fft_filter(
            image=pattern,
            fft_shape=fft_shape,
            window_shape=kernel_shape,
            window_fft=kernel_fft,
            offset_before_fft=offset_before_fft,
            offset_after_ifft=offset_after_ifft,
        )
    elif filter_domain == "spatial":
        dynamic_bg = gaussian_filter(
            input=pattern, sigma=std, truncate=truncate,
        )
    else:
        filter_domains = ["frequency", "spatial"]
        raise ValueError(f"{filter_domain} must be either of {filter_domains}.")

    # Remove dynamic background
    if operation == "subtract":
        corrected_pattern = pattern - dynamic_bg
    else:  # operation == "divide"
        corrected_pattern = pattern / dynamic_bg

    # Rescale intensity
    corrected_pattern = rescale_intensity(
        corrected_pattern, dtype_out=dtype_out
    )

    return corrected_pattern


def _dynamic_background_frequency_space_setup(
    pattern_shape: Union[List[int], Tuple[int, ...]],
    std: Union[int, float],
    truncate: Union[int, float],
) -> Tuple[
    Tuple[int, ...],
    Tuple[int, ...],
    np.ndarray,
    Tuple[int, ...],
    Tuple[int, ...],
]:
    # Get Gaussian filtering window
    shape = (int(truncate * std),) * 2
    window = Window("gaussian", std=std, shape=shape)
    window = window / (2 * np.pi * std ** 2)
    window = window / np.sum(window)

    # FFT filter setup
    (
        fft_shape,
        kernel_rfft,
        offset_before_fft,
        offset_after_ifft,
    ) = _fft_filter_setup(pattern_shape, window)

    return (
        fft_shape,
        window.shape,
        kernel_rfft,
        offset_before_fft,
        offset_after_ifft,
    )


def get_dynamic_background(
    pattern: np.ndarray,
    filter_domain: str = "frequency",
    std: Union[None, int, float] = None,
    truncate: Union[int, float] = 4.0,
) -> np.ndarray:
    """Get the dynamic background in an EBSD pattern.

    The background is obtained either in the frequency domain, by a low
    pass Fast Fourier Transform (FFT) Gaussian filter, or in the spatial
    domain by a Gaussian filter.

    Data type is preserved.

    Parameters
    ----------
    pattern
        EBSD pattern.
    filter_domain
        Whether to obtain the dynamic background by applying a Gaussian
        convolution filter in the "frequency" (default) or "spatial"
        domain.
    std
        Standard deviation of the Gaussian window. If None (default), a
        deviation of pattern width/8 is chosen.
    truncate
        Truncate the Gaussian window at this many standard deviations.
        Default is 4.0.

    Returns
    -------
    dynamic_bg
        The dynamic background.

    """

    if std is None:
        std = pattern.shape[1] / 8

    if filter_domain == "frequency":
        (
            fft_shape,
            kernel_shape,
            kernel_fft,
            offset_before_fft,
            offset_after_ifft,
        ) = _dynamic_background_frequency_space_setup(
            pattern_shape=pattern.shape, std=std, truncate=truncate,
        )
        dynamic_bg = _fft_filter(
            image=pattern,
            fft_shape=fft_shape,
            window_shape=kernel_shape,
            window_fft=kernel_fft,
            offset_before_fft=offset_before_fft,
            offset_after_ifft=offset_after_ifft,
        )
    elif filter_domain == "spatial":
        dynamic_bg = gaussian_filter(
            input=pattern, sigma=std, truncate=truncate,
        )
    else:
        filter_domains = ["frequency", "spatial"]
        raise ValueError(f"{filter_domain} must be either of {filter_domains}.")

    return dynamic_bg.astype(pattern.dtype)


def get_image_quality(
    pattern: np.ndarray,
    normalize: bool = True,
    frequency_vectors: Optional[np.ndarray] = None,
    inertia_max: Union[None, int, float] = None,
) -> float:
    """Return the image quality of an EBSD pattern.

    The image quality is calculated based on the procedure defined by
    Krieger Lassen [Lassen1994]_.

    Parameters
    ----------
    pattern
        EBSD pattern.
    normalize
        Whether to normalize the pattern to a mean of zero and standard
        deviation of 1 before calculating the image quality (default is
        True).
    frequency_vectors
        Integer 2D array assigning each FFT spectrum frequency component
        a weight. If None (default), these are calculated from
        :func:`~kikuchipy.util.experimental.fft_frequency_vectors`.
    inertia_max
        Maximum inertia of the FFT power spectrum of the image. If None
        (default), this is calculated from the `frequency_vectors`,
        which in this case *must* be passed.

    Returns
    -------
    image_quality
        Image quality of the image.

    Notes
    -----
    The parameters `frequency_vectors` and `inertia_max` depend only on
    the image shape in pixels.

    """

    if frequency_vectors is None:
        sy, sx = pattern.shape
        frequency_vectors = fft_frequency_vectors((sy, sx))

    if inertia_max is None:
        sy, sx = pattern.shape
        inertia_max = np.sum(frequency_vectors) / (sy * sx)

    if normalize is True:
        pattern = normalize_intensity(pattern)

    # Compute FFT
    fft_pattern = fft(pattern)

    # Obtain (un-shifted) FFT spectrum
    spectrum = fft_spectrum(fft_pattern)

    # Calculate inertia (see Lassen1994)
    inertia = np.sum(spectrum * frequency_vectors) / np.sum(spectrum)

    return 1 - (inertia / inertia_max)


def fft(
    pattern: np.ndarray,
    shift: bool = False,
    apodization: Union[bool, str] = False,
    real_fft_only: bool = False,
    **kwargs,
) -> np.ndarray:
    """Compute the discrete Fast Fourier Transform (FFT) of an EBSD
    pattern.

    This function is adapted from HyperSpy.

    Parameters
    ----------
    pattern
        EBSD pattern.
    shift
        Whether to shift the zero-frequency component to the centre of
        the spectrum (default is False).
    apodization
        Apply an apodization window before the FFT in order to suppress
        streaks. This is not implemented yet.
    real_fft_only
        If True, the discrete FFT is computed for real input using
        :func:`scipy.fft.rfft2`. If False (default), it is computed
        using :func:`scipy.fft.fft2`.
    kwargs :
        Keyword arguments pass to :func:`scipy.fft.fft2` or
        :func:`scipy.fft.rfft2`.

    Returns
    -------
    out
        The result of the 2D FFT.

    """

    if apodization:
        raise NotImplementedError()

    if real_fft_only:
        fft_use = scipy.fft.rfft2
    else:
        fft_use = scipy.fft.fft2

    if shift:
        out = scipy.fft.fftshift(fft_use(pattern, **kwargs))
    else:
        out = fft_use(pattern, **kwargs)

    return out


def ifft(fft_pattern: np.ndarray, shift: bool = False, **kwargs) -> np.ndarray:
    """Compute the inverse Fast Fourier Transform (IFFT) of an FFT of an
    EBSD pattern.

    Parameters
    ----------
    fft_pattern
        FFT of EBSD pattern.
    shift
        Whether to shift the zero-frequency component back to the
        corners of the spectrum (default is False).
    kwargs :
        Keyword arguments pass to :func:`scipy.fft.ifft`.

    Returns
    -------
    pattern
        Real part of the IFFT of the EBSD pattern.

    """

    if shift:
        pattern = scipy.fft.ifft2(scipy.fft.ifftshift(fft_pattern, **kwargs))
    else:
        pattern = scipy.fft.ifft2(fft_pattern, **kwargs)

    return pattern.real


@njit
def fft_spectrum(fft_pattern: np.ndarray) -> np.ndarray:
    """Compute FFT spectrum of a Fourier transformed EBSD pattern.

    Parameters
    ----------
    fft_pattern
        Fourier transformed EBSD pattern.

    Returns
    -------
    fft_spectrum
        2D FFT spectrum of the EBSD pattern.

    """

    return np.sqrt(fft_pattern.real ** 2 + fft_pattern.imag ** 2)


@njit
def normalize_intensity(
    pattern: np.ndarray, num_std: int = 1, divide_by_square_root: bool = False
) -> np.ndarray:
    """Normalize image intensities to a mean of zero and a given
    standard deviation.

    Parameters
    ----------
    pattern
        2D experimental EBSD image.
    num_std
        Number of standard deviations of the output intensities (default
        is 1).
    divide_by_square_root
        Whether to divide output intensities by the square root of the
        image size (default is False).

    Returns
    -------
    normalized_pattern
        Normalized image.

    """

    pattern_mean = np.mean(pattern)
    pattern_std = np.std(pattern)

    if divide_by_square_root:
        return (pattern - pattern_mean) / (
            num_std * pattern_std * np.sqrt(pattern.size)
        )
    else:
        return (pattern - pattern_mean) / (num_std * pattern_std)


def fft_frequency_vectors(shape: Tuple[int, int]) -> np.ndarray:
    sy, sx = shape

    linex = np.arange(sx) + 1
    linex[sx // 2 :] -= sx + 1
    liney = np.arange(sy) + 1
    liney[sy // 2 :] -= sy + 1

    frequency_vectors = np.empty(shape=(sy, sx))
    for i in range(sy):
        frequency_vectors[i] = liney[i] ** 2 + linex ** 2 - 1

    return frequency_vectors
