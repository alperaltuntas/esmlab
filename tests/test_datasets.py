#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

import os

import xarray as xr

from esmlab.datasets import open_dataset


def test_open_dataset():
    ds = open_dataset('cesm_pop_yearly')
    assert isinstance(ds, xr.Dataset)


def test_open_dataset_cache():
    ds = open_dataset('ncep_forecast_tseries', cache=False)
    assert isinstance(ds, xr.Dataset)
    assert not os.path.exists(os.path.abspath('~/.esmlab_data/ncep_forecast_tseries.nc'))
