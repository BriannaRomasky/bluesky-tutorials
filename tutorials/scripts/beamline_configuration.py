import os

# Set some enviornment variables before importing pyepics.
os.environ['EPICS_CAS_AUTO_BEACON_ADDR_LIST'] = 'no'
os.environ['EPICS_CA_AUTO_ADDR_LIST'] = 'no'
os.environ['EPICS_CAS_BEACON_ADDR_LIST'] = '127.0.0.1'
os.environ['EPICS_CA_ADDR_LIST'] = '127.0.0.1'

import matplotlib

matplotlib.use('nbAgg')  # i.e. %matplotlib notebook
import matplotlib.pyplot
matplotlib.use('nbAgg', force=True)  # i.e. %matplotlib notebook

from ophyd import Device, Component, EpicsSignal
from ophyd.signal import EpicsSignalBase
from ophyd.areadetector.filestore_mixins import resource_factory
import uuid
import os
from pathlib import Path
import numpy as np
from IPython import get_ipython

# Set up a RunEngine and use metadata backed by a sqlite file.
from bluesky import RunEngine
from bluesky.utils import get_history
RE = RunEngine(get_history())

# Set up SupplementalData.
from bluesky import SupplementalData
sd = SupplementalData()
RE.preprocessors.append(sd)

# Set up a Broker.
from databroker import Broker
db = Broker.named('temp')

# and subscribe it to the RunEngine
RE.subscribe(db.insert)

# Add a progress bar.
from bluesky.utils import ProgressBarManager
pbar_manager = ProgressBarManager()
RE.waiting_hook = pbar_manager

# Register bluesky IPython magics.
from bluesky.magics import BlueskyMagics
get_ipython().register_magics(BlueskyMagics)

# Set up the BestEffortCallback.
from bluesky.callbacks.best_effort import BestEffortCallback
bec = BestEffortCallback()
RE.subscribe(bec)
peaks = bec.peaks

# Import matplotlib and put it in interactive mode.
import matplotlib.pyplot as plt
plt.ion()

# Make plots update live while scans run.
from bluesky.utils import install_kicker
install_kicker()

# convenience imports
# some of the * imports are for 'back-compatibility' of a sort -- we have
# taught BL staff to expect LiveTable and LivePlot etc. to be in their
# namespace
import numpy as np

import bluesky.callbacks
from bluesky.callbacks import *

import bluesky.plans
from bluesky.plans import *

import bluesky.plan_stubs
from bluesky.plan_stubs import *

import bluesky.preprocessors
import bluesky.simulators
from bluesky.simulators import *


class Det(Device):
    det = Component(EpicsSignal, ':det', kind='hinted')
    exp = Component(EpicsSignal, ':exp', kind='config')

# here there be 🐉🐉🐉🐉🐉🐉


class ArraySignal(EpicsSignalBase):
    def __init__(self, read_pv, **kwargs):
        super().__init__(read_pv, **kwargs)
        cl = self.cl
        base_pv, _ = read_pv.rsplit(':', maxsplit=1)
        self._size_pv = cl.get_pv(
            ':'.join((base_pv, 'ArraySize_RBV')))

        self._last_ret = None
        self._asset_docs_cache = []

    def trigger(self):
        os.makedirs('/tmp/demo', exist_ok=True)
        st = super().trigger()
        ret = super().read()
        val = ret[self.name]['value'].reshape(self._size_pv.get())

        resource, datum_factory = resource_factory(
            spec='npy',
            root='/tmp',
            resource_path=f'demo/{uuid.uuid4()}.npy',
            resource_kwargs={},
            path_semantics='posix')
        datum = datum_factory({})
        self._asset_docs_cache.append(('resource', resource))
        self._asset_docs_cache.append(('datum', datum))
        fpath = Path(resource['root']) / resource['resource_path']
        np.save(fpath, val)

        ret[self.name]['value'] = datum['datum_id']
        self._last_ret = ret
        return st

    def describe(self):
        ret = super().describe()
        ret[self.name]['shape'] = [int(k)
                                   for k in
                                   self._size_pv.get()]
        ret[self.name]['external'] = 'FILESTORE:'
        del ret[self.name]['upper_ctrl_limit']
        del ret[self.name]['lower_ctrl_limit']
        return ret

    def read(self):
        if self._last_ret is None:
            raise Exception('read before being triggered')
        return self._last_ret

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


class Spot(Device):
    img = Component(ArraySignal, ':det')
    roi = Component(EpicsSignal, ':img_sum', kind='hinted')
    exp = Component(EpicsSignal, ':exp', kind='config')
    shutter_open = Component(EpicsSignal, ':shutter_open', kind='config')

    def collect_asset_docs(self):
        yield from self.img.collect_asset_docs()

    def trigger(self):
        return self.img.trigger()


ph = Det('mini:ph', name='ph')
edge = Det('mini:edge', name='edge')
slit = Det('mini:slit', name='slit')

motor_ph = EpicsSignal('mini:ph:mtr',
                       name='motor_ph')
motor_edge = EpicsSignal('mini:edge:mtr',
                         name='motor_edge')
motor_slit = EpicsSignal('mini:slit:mtr',
                         name='motor_slit')

spot = Spot('mini:dot', name='spot')
mtr_spotx = EpicsSignal('mini:dot:mtrx',
                        name='motor_spotx')
mtr_spoty = EpicsSignal('mini:dot:mtry',
                        name='motor_spoty')

I = EpicsSignal('mini:current', name='I')
