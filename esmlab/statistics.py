#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

from warnings import warn

import numpy as np
import xarray as xr

from .utils.common import esmlab_xr_set_options
from .utils.variables import (
    get_original_attrs,
    get_static_variables,
    get_variables,
    save_metadata,
    set_metadata,
    set_static_variables,
    update_attrs,
)


def _get_weights_and_dims(x, y=None, weights=None, dim=None):
    """ Get weights and dimensions """

    if dim and isinstance(dim, str):
        dims = [dim]

    elif isinstance(dim, list):
        dims = dim

    else:
        dims = [k for k in x.dims]

    op_over_dims = [k for k in dims if k in x.dims]
    if not op_over_dims:
        raise ValueError("Unexpected dimensions for variable {0}".format(x.name))

    dims_shape = tuple(l for i, l in enumerate(x.shape) if x.dims[i] in op_over_dims)
    if weights is None:
        weights = xr.DataArray(np.ones(dims_shape), dims=op_over_dims)

    else:
        assert weights.shape == dims_shape

    # If y is specified, make sure x and y have same shape
    if y is not None and isinstance(y, xr.DataArray):
        assert x.shape == y.shape
        valid = x.notnull() & y.notnull()
    else:
        valid = x.notnull()

    # Apply nan mask
    weights = weights.where(valid)

    # Make sure weights add up to 1.0
    np.testing.assert_allclose(
        (weights / weights.sum(op_over_dims)).sum(op_over_dims), 1.0
    )
    return weights, op_over_dims


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_sum(x, weights=None, dim=None):
    """Reduce DataArray by applying `weighted sum` along some dimension(s).

            Parameters
            ----------

            x : DataArray object
               xarray object for which to compute `weighted sum`.

            weights : array_like, default `None`
                    weights to use

            dim : str or sequence of str, optional
                Dimension(s) over which to apply mean. By default `weighted sum`
                is applied over all dimensions.

            Returns
            -------

            reduced : DataArray
                New DataArray object with `weighted sum` applied to its data
                and the indicated dimension(s) removed. If `weights` is None,
                returns regular sum with equal weights for all data points.
    """
    if weights is None:
        warn("Computing sum with equal weights for all data points")

    weights, op_over_dims = _get_weights_and_dims(x, weights=weights, dim=dim)
    x_w_sum = (x * weights).sum(op_over_dims)

    original_attrs, original_encoding = get_original_attrs(x)
    return update_attrs(x_w_sum, original_attrs, original_encoding)


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_mean(x, weights=None, dim=None):
    """Reduce DataArray by applying weighted mean along some dimension(s).

        Parameters
        ----------

        x : DataArray object
           xarray object for which to compute `weighted mean`.

        weights : array_like

        dim : str or sequence of str, optional
           Dimension(s) over which to apply `weighted mean`. By default weighted mean
           is applied over all dimensions.


        Returns
        -------

        reduced : DataArray
             New DataArray object with ` weighted mean` applied to its data
             and the indicated dimension(s) removed. If `weights` is None,
                returns regular mean with equal weights for all data points.
    """
    if weights is None:
        warn("Computing mean with equal weights for all data points")

    weights, op_over_dims = _get_weights_and_dims(x, weights=weights, dim=dim)

    x_w_mean = weighted_sum(x, weights=weights, dim=op_over_dims) / weights.sum(
        op_over_dims
    )
    original_attrs, original_encoding = get_original_attrs(x)
    return update_attrs(x_w_mean, original_attrs, original_encoding)


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_std(x, weights=None, dim=None, ddof=0):
    """Reduce DataArray by applying `weighted std` along some dimension(s).

        Parameters
        ----------

        x : DataArray object
           xarray object for which to compute `weighted std`.

        weights : array_like

        dim : str or sequence of str, optional
           Dimension(s) over which to apply mean. By default `weighted std`
           is applied over all dimensions.


        ddof : int, optional
            Means Delta Degrees of Freedom. By default ddof is zero.


        Returns
        -------

        weighted_standard_deviation : DataArray
             New DataArray object with `weighted std` applied to its data
             and the indicated dimension(s) removed. If `weights` is None,
                returns regular standard deviation with equal weights for all data points.
    """
    if weights is None:
        warn("Computing standard deviation with equal weights for all data points")

    weights, op_over_dims = _get_weights_and_dims(x, weights=weights, dim=dim)

    x_w_mean = weighted_mean(x, weights=weights, dim=op_over_dims)

    x_w_std = np.sqrt(
        (weights * (x - x_w_mean) ** 2).sum(op_over_dims)
        / (weights.sum(op_over_dims) - ddof)
    )
    original_attrs, original_encoding = get_original_attrs(x)

    return update_attrs(x_w_std, original_attrs, original_encoding)


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_rmsd(x, y, weights=None, dim=None):
    """ Compute weighted root-mean-square-deviation between two `xarray` DataArrays.

    Parameters
    ----------

    x, y : DataArray objects
        xarray objects for which to compute `weighted_rmsd`.
    weights : array_like
    dim : str or sequence of str, optional
           Dimension(s) over which to apply `weighted rmsd` By default weighted rmsd
           is applied over all dimensions.

    Returns
    -------

    weighted_root_mean_square deviation : float

    """

    if weights is None:
        warn(
            "Computing root-mean-square-deviation with equal weights for all data points"
        )

    weights, op_over_dims = _get_weights_and_dims(x=x, y=y, weights=weights, dim=dim)
    dev = (x - y) ** 2
    dev_mean = weighted_mean(dev, weights=weights, dim=op_over_dims)
    return np.sqrt(dev_mean)


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_cov(x, y, weights=None, dim=None):
    """ Compute weighted covariance between two `xarray` DataArrays.

    Parameters
    ----------

    x, y : DataArray objects
        xarray objects for which to compute `weighted covariance`.
    weights : array_like
    dim : str or sequence of str, optional
           Dimension(s) over which to apply `weighted covariance`
           By default weighted covariance is applied over all dimensions.

    Returns
    -------

    weighted_covariance : float

    """
    if weights is None:
        warn("Computing weighted covariance with equal weights for all data points")

    weights, op_over_dims = _get_weights_and_dims(x=x, y=y, weights=weights, dim=dim)
    mean_x = weighted_mean(x, weights=weights, dim=op_over_dims)
    mean_y = weighted_mean(y, weights=weights, dim=op_over_dims)

    dev_x = x - mean_x
    dev_y = y - mean_y
    dev_xy = dev_x * dev_y
    cov_xy = weighted_mean(dev_xy, weights=weights, dim=op_over_dims)
    return cov_xy


@esmlab_xr_set_options(arithmetic_join="exact")
def weighted_corr(x, y, weights=None, dim=None):
    """ Compute weighted correlation between two `xarray` DataArrays.

    Parameters
    ----------

    x, y : DataArray objects
        xarray objects for which to compute `weighted correlation`.
    weights : array_like
    dim : str or sequence of str, optional
           Dimension(s) over which to apply `weighted correlation`
           By default weighted correlation is applied over all dimensions.

    Returns
    -------

    weighted_correlation : float

    """
    if weights is None:
        warn("Computing weighted correlation with equal weights for all data points")

    weights, op_over_dims = _get_weights_and_dims(x=x, y=y, weights=weights, dim=dim)
    numerator = weighted_cov(x=x, y=y, weights=weights, dim=op_over_dims)
    denominator = np.sqrt(
        weighted_cov(x, x, weights=weights, dim=op_over_dims)
        * weighted_cov(y, y, weights=weights, dim=op_over_dims)
    )
    corr_xy = numerator / denominator
    return corr_xy
