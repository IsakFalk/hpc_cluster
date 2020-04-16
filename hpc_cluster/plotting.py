"""Make plotting easier when dealing with the output of server jobs

After running a server job, your data will reside in a job output directory.
If you ran experiment A then this will be saved in the directory A with structure
A\n{1-N} where N is the number of jobs in your array job. Customarily each job k will
look as follows
A\n{k}\experiment_data.hkl
      \parameters.hkl

In order to plot this efficiently each directory need to be read and fed into the function
for plotting."""
from pathlib import Path
import logging
import os
import re
import math

import matplotlib as mpl
import matplotlib.pyplot as plt
import hickle as hkl

class GridPlot:
    """Plot the result of an array-job in a grid

    For an array job with N jobs, plot the jobs in a
    grid."""
    
    data_dir_match_regexp = r"n[1-9]\d*"
    
    def __init__(self,
                 experiment_dir,
                 preprocess_func,
                 plot_func,
                 figtitle=None,
                 nrows=None,
                 ncols=None,
                 force_balanced_layout=False):
        """
        :param experiment_dir: (pathlib.Path) path to the output of array job
        :param preprocess_func: (func) function for preprocessing the data and parameters from one task of the array job
        :param plot_func: (func) function for plotting one task of the array job
        :param figtitle: (str) title of figure, suptitle
        :param nrows: (int) number of rows in ax grid
        :param ncols: (int) number of columns in ax grid
        :param force_balanced_layout: (bool) only accept layouts such that {number of tasks} == nrows * ncols
        """
        self.experiment_dir = experiment_dir
        self.preprocess_func = preprocess_func
        self.plot_func = plot_func
        self.figtitle = figtitle
        self.nrows = nrows
        self.ncols = ncols
        self.force_balanced_layout = force_balanced_layout

        self._find_data_dirs()
        self.n_data_dirs = len(self.data_dirs)
        self._autoset_layout()
        self._check_layout()

        self._plotted = False
        
    def _find_data_dirs(self):
        """Walk experiment_dir to find data dirs

        We assume that the data-dirs live immediately
        below experiment_dir."""
        self.data_dirs = []
        for root, dirs, files in os.walk(self.experiment_dir):
            for dir in dirs:
                if re.match(self.data_dir_match_regexp, str(dir)):
                    self.data_dirs.append(Path(root) / Path(dir))
            break
        # Preliminarily sort by n{digit}
        self.data_dirs = sorted(self.data_dirs, key=lambda relative_dir: int(relative_dir.name.replace("n", "")))
        assert len(self.data_dirs) != 0, "Make sure there are at least one data directory in the experiment_dir"

    def _autoset_layout(self):
        """If nrows or ncols are None, we make this grid in a smart way"""
        if self.nrows is None and self.ncols is None:
            self.nrows = math.ceil(math.sqrt(self.n_data_dirs))
            self.ncols = math.ceil(math.sqrt(self.n_data_dirs))
        elif self.nrows is None:
            div, rem = divmod(self.n_data_dirs, self.ncols)
            self.nrows = div + math.ceil(rem / self.ncols)
        elif self.ncols is None:
            div, rem = divmod(self.n_data_dirs, self.nrows)
            self.ncols = div + math.ceil(rem / self.nrows)
        
    def _check_layout(self):
        """Fail if layout is misspecified"""
        assert self.nrows * self.ncols >= len(self.data_dirs), "Number of spaces in grid must be more than number of data dirs"
        if self.force_balanced_layout:
            assert self.nrows * self.ncols == len(self.data_dirs), "force_balanced_layout == True: the data directories does not fill axis grid."

    @staticmethod        
    def _read_data_dir(data_dir):
        """Read experiment_data.hkl and parameters.hkl from data_dir"""
        experiment_data = hkl.load(data_dir / 'experiment_data.hkl')
        parameters = hkl.load(data_dir / 'parameters.hkl')
        return experiment_data, parameters
            
    def plot(self, tight_layout=False, **subplots_kwargs):
        """Plot the result from reading and preprocessing data dirs"""
        fig, ax = plt.subplots(nrows=self.nrows, ncols=self.ncols, **subplots_kwargs)
        self.fig = fig
        self.ax = ax
        # Unroll ax to a contiguous array,
        # this allows us to plot easily using a for loop.
        # Note that ravel follows C-ordering, row indices
        # change slowest
        for data_dir, axis in zip(self.data_dirs, self.ax.ravel()):
            experiment_data, parameters = self._read_data_dir(data_dir)
            preprocessed_data = self.preprocess_func(experiment_data, parameters)
            self.plot_func(preprocessed_data, axis)
        if self.figtitle is not None:
            fig.suptitle(self.figtitle)
        if tight_layout:
            plt.tight_layout()
        self._plotted = True

    def savefig(self, savepath, **savefig_kwargs):
        """Save figure"""
        if not self._plotted:
            self.plot()
        self.fig.savefig(savepath, **savefig_kwargs)
