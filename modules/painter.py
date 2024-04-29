#!/usr/bin/env python3
"""painter: A custom figure interface

Classes
-------
Painter()
    A figure interface class
"""

import os
import re
import subprocess
import matplotlib.pyplot as plt
from matplotlib import rcParams, patches
from matplotlib.ticker import AutoMinorLocator
from matplotlib.lines import Line2D

__author__ = 'Jaewoong Jang'
__copyright__ = 'Copyright (c) 2024 Jaewoong Jang'
__license__ = 'MIT License'
__version__ = '1.0.0'
__date__ = '2024-04-28'


class Painter():
    """A figure interface class.

    Parameters
    ----------
    dflt_style_sheet : str, optional
        A default matplotlib style sheet. The default is 'bmh'.

    Attributes
    ----------
    is_drawn : dict
        A dictionary to hold information if certain artists have been drawn.

    Methods
    -------
    sortkey_nat(s, tup_ordinal=0)
        Decompose a string for natural sorting.
    sort_legend(handles, labels, is_reverse=False)
        Sort an MPL legend.
    set_rc_params(rc_params)
        Apply user-designated MPL rcParams parameters.
    set_plot_style(d)
        Apply MPL style configurations designated by the user.
    set_markers(self, mrks_def, mrks_dflt, sep1=',', sep2='+',
                is_verbose=False)
        Create a dictionary of marker attributes using one-line strings.
    plot_radiat_spectr(fig, ax, p, df, cols,
                       x='energy', y='emission_probability',
                       plot_type='spectrum',
                       is_spotting=False, is_finalize=True)
        Plot a radiation spectrum and/or its associated radionuclides.
    save_fig(fig, out_path, out_bname, fmts,
             dpi=300, inkscape_exe='inkscape.exe')
        Save an MPL figure in multiple formats.
    run_pdf_postproc(pdf_fname_full,
                     is_gs=True, gs_exe='gswin64.exe', gs_pdf_ver=1.5,
                     is_pdfcrop=True, pdfcrop_exe='pdfcrop.exe')
        Postprocess a .pdf figure file.
    """

    def __init__(self,
                 dflt_style_sheet='bmh'):
        """Initialize an object of the Painter class.

        Parameters
        ----------
        dflt_style_sheet : str, optional
            A default matplotlib style sheet. The default is 'bmh'.

        Returns
        -------
        None.
        """
        plt.style.use(dflt_style_sheet)
        _artists = ['title']
        self.is_drawn = {a: False for a in _artists}

    def sortkey_nat(self, s,
                    tup_ordinal=0):
        """Decompose a string for natural sorting.

        Parameters
        ----------
        s : str
            A string to be decomposed for natural sorting.
        tup_ordinal : int, optional
            The ordinal of a string in a tuple. The default is 0.

        Returns
        -------
        naturalized : list
            A list containing the subcomponents of the input string.

        Notes
        -----
        This function was inspired by the one posted at:
        https://stackoverflow.com/questions/4836710
        """
        # For a tuple, use one of its elements.
        if isinstance(s, tuple):
            s = s[tup_ordinal]
        naturalized = [int(t) if t.isdigit() else t.lower()
                       for t in re.split('([0-9]+)', s)]
        return naturalized

    def sort_legend(self, handles, labels,
                    is_reverse=False):
        """Sort an MPL legend.

        Parameters
        ----------
        handles : list
            A list of MPL handles to be sorted parallelly with labels.
        labels : list
            A list of MPL labels to be sorted.
        is_reverse : bool, optional
            If True, the handles and labels will be sorted in descending
            order of labels. The default is False.

        Returns
        -------
        handles_sorted : list
            A list of sorted handles.
        labels_sorted : list
            A list of sorted labels.
        """
        labels_sorted, handles_sorted = [
            list(tup) for tup
            in zip(*sorted(zip(labels, handles),
                           key=self.sortkey_nat, reverse=is_reverse))]
        return handles_sorted, labels_sorted

    def set_rc_params(self, rc_params):
        """Apply user-designated MPL rcParams parameters.

        Parameters
        ----------
        rc_params : dict
            A dictionary containing rcParams specifications.
        """
        for k in rc_params:
            rcParams[k] = rc_params[k]

    def set_plot_style(self, d):
        """Apply MPL style configurations designated by the user.

        Parameters
        ----------
        d : dict
            A dictionary containing MPL style designations.

        Returns
        -------
        None.
        """
        #
        # Global MPL style
        #
        if 'style_sheet' in d:
            plt.style.use(d['style_sheet'])
        if 'rc_params' in d and d['rc_params'] is not None:
            self.set_rc_params(d['rc_params'])

        #
        # Bar style
        #
        if 'bar' in d:
            hatches = []
            facecolors = []
            if 'hatches' in d['bar']:
                for hatch in d['bar']['hatches']:
                    hatch = None if re.search('(?i)none', hatch) else hatch
                    hatches.append(hatch)
            if 'facecolors' in d['bar']:
                facecolors += d['bar']['facecolors']
            # Spare items in case that the designated ones are insufficient
            # compared with the number of datasets being plotted (equal to
            # the number of legend labels)
            hatches += [None, '//', '*', '\\', '-',
                        '+', 'x', 'o', 'O', '.', '*']
            facecolors += ['tab:blue', 'tab:orange', 'tab:green',
                           'tab:red', 'tab:purple']
            d['bar']['hatches'] = hatches
            d['bar']['facecolors'] = facecolors

    def set_markers(self, mrks_def, mrks_dflt,
                    sep1=',', sep2='+', is_verbose=False):
        """Create a dictionary of marker attributes using one-line strings.

        Parameters
        ----------
        mrks_def : list
            A list of one-line marker specification strings.
        mrks_dflt : dict
            A dictionary of default marker specifications to fill in
            unspecified marker attributes.
        sep1 : str, optional
            A first-level separator delimiting marker attributes.
            The default is ','.
        sep2 : str, optional
            A second-level separator delimiting filled marker attributes.
            The default is '+'.
        is_verbose : TYPE, optional
            If True, the created marker attributes will be displayed.
            The default is False.

        Returns
        -------
        mrks : dict
            A dictionary containing marker attributes generated by
            interpreting mrks_def and mixing with mrks_dflt.
        """
        mrk_attrs = ['msymb', 'mfc', 'mec', 'mew', 'msz', 'alpha']
        mrks = {attr: [] for attr in mrk_attrs}
        for m in mrks_def:
            #
            # Split a one-line marker specification string into
            # marker attribute specifications.
            #
            mlist = re.split(r'\s*[{}]\s*'.format(sep1), m)
            #
            # Attribute 1: marker symbol
            #
            try:
                # Integer markers; e.g. 4 (CARETLEFT), 5 (CARETRIGHT), ...
                # Exception: "8" for octagon
                if not re.search('8', mlist[0]):
                    mlist[0] = int(mlist[0])
            except ValueError:
                pass
            mrks['msymb'].append(mlist[0])
            #
            # Attribute 2: markerfacecolor, markeredgecolor, markeredgewidth
            #
            if len(mlist) >= 2:
                msublist = re.split(r'\s*[{}]\s*'.format(sep2), mlist[1])
                mrks['mfc'].append(msublist[0])
                if len(msublist) >= 2:
                    mrks['mec'].append(msublist[1])
                else:
                    mrks['mec'].append(mrks_dflt['mec'])
                if len(msublist) == 3:
                    mrks['mew'].append(float(msublist[2]))
                else:
                    mrks['mew'].append(mrks_dflt['mew'])
            else:
                for attr2 in ['mfc', 'mec', 'mew']:
                    mrks[attr2].append(mrks_dflt[attr2])
            #
            # Attribute 3: markersize
            #
            if len(mlist) >= 3:
                mrks['msz'].append(float(mlist[2]))
            else:
                mrks['msz'].append(mrks_dflt['msz'])
            #
            # Attribute 4: alpha
            #
            if len(mlist) == 4:
                mrks['alpha'].append(float(mlist[3]))
            else:
                mrks['alpha'].append(mrks_dflt['alpha'])
        if is_verbose:
            for attr in mrks.keys():
                print(f'attr: {attr}, len(mrks[attr]): {len(mrks[attr])},',
                      f' mrks[attr]: {mrks[attr]}')
        return mrks

    def plot_radiat_spectr(self, fig, ax, p, df, cols,
                           x='energy', y='emission_probability',
                           plot_type='spectrum',
                           is_spotting=False, is_finalize=True):
        """Plot a radiation spectrum and/or its associated radionuclides.

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            An MPL Figure object.
        ax : matplotlib.axes._axes.Axes
            An MPL Axes object.
        p : dict
            A dictionary containing user-specified plotting configurations.
        df : pandas.core.frame.DataFrame
            A DF holding datasets to be plotted.
        cols : dict
            A dictionary holding DF column names.
        x : str, optional
            The name of a DF column to be used as x-axis data.
            The default is 'energy'.
        y : str, optional
            The name of a DF column to be used as y-axis data.
            The default is 'emission_probability'.
        plot_type : str, optional
            A plot type. Available values are ['spectrum', 'rn'].
            The default is 'spectrum'.
        is_spotting : bool, optional
            If True, some of the commands related to plot_type == 'rn' are
            customized for radionuclide identification settings.
            The default is False.
        is_finalize : bool, optional
            If True, the generated figure will be saved to files.
            If False, the function will terminate without modifying the figure
            base name and without running the figure saving command block.
            The default is True.

        Returns
        -------
        None.
            is_finalize == False will terminate the function by returning None.
        """
        #
        # x-axis
        #
        if not p['plot']['xticks']['is_auto']:
            xlim = [float(n) for n in p['plot']['xticks']['lim']]
            ax.set_xlim(xlim)
        if 'minor_ndivs' in p['plot']['xticks']:
            mxticks = p['plot']['xticks']['minor_ndivs']
            ax.xaxis.set_minor_locator(AutoMinorLocator(mxticks))
        ax.tick_params(axis='x', which='major',
                       **p['plot']['xticks']['kwargs'])
        if not p['plot']['xticks']['is_ticklabels']:
            ax.xaxis.set_ticklabels([])
        if p['plot']['xticks']['is_remove_end_ticklabels']:
            _xticklabels = ax.get_xticklabels()
            _xticklabels[0].set_text('')
            _xticklabels[-1].set_text('')
            ax.xaxis.set_ticklabels(_xticklabels)
        if p['plot']['xlabel']['toggle']:
            ax.set_xlabel(p['plot']['xlabel']['label'],
                          **p['plot']['xlabel']['kwargs'])

        #
        # Figure base name modification (1/4)
        # Use a local variable, in place of the dictionary variable, holding
        # a figure base name to avoid its repetitive modifications.
        #
        out_fig_bname = p['io']['out']['fig_bname']

        #
        # Figure base name modification (2/4)
        # - Append the values of energy range to the figure base name.
        # - Use the bool is_finalize to avoid repetitive modifications
        #   when this function is called multiple times.
        #
        if is_finalize:
            out_fig_bname += '_nrg{}-{}'.format(
                int(ax.get_xlim()[0]),
                int(ax.get_xlim()[1]))

        #
        # Figure base name modification (3/4)
        # - Append the plot type to the figure base name.
        #
        out_fig_bname += '_{}'.format(plot_type)

        #
        # y-axis
        #
        if p['plot']['yticks']['is_log']:
            ax.set_yscale('log')
            ax.yaxis.get_major_locator().set_params(
                **p['plot']['yticks']['log_locators']['major'])
            ax.yaxis.get_minor_locator().set_params(
                **p['plot']['yticks']['log_locators']['minor'])
        if not p['plot']['yticks']['is_auto']:
            ylim = [float(n) for n in p['plot']['yticks']['lim']]
            ax.set_ylim(ylim)
        ax.tick_params(axis='y', which='major',
                       **p['plot']['yticks']['kwargs'])
        if not p['plot']['yticks']['is_ticklabels']:
            ax.yaxis.set_ticklabels([])
        if p['plot']['ylabel']['toggle']:
            ax.set_ylabel(p['plot']['ylabel']['label'],
                          **p['plot']['ylabel']['kwargs'])

        #
        # Data column type selection
        #
        data_col_type = 'nucl_data_new'
        if is_spotting:
            data_col_type = 'spectrum'

        #
        # Plotting: A radiation spectrum
        #
        if re.search('(?i)spectrum|line', plot_type):
            xdata_spectr = df[cols[x][data_col_type]].copy()
            ydata_spectr = df[cols[y][data_col_type]].copy()
            ax.plot(xdata_spectr, ydata_spectr,
                    # A radiation spectrum will be placed above, if any,
                    # annotation markers for spotted radionuclides.
                    zorder=10,
                    **p['plot']['line2d']['kwargs'])

        #
        # Title
        #
        if (p['plot']['title']['toggle']
                and not self.is_drawn['title']):
            if ('label' in p['plot']['title']
                    and p['plot']['title']['label']):
                the_title = p['plot']['title']['label']
            else:
                the_title = out_fig_bname
            # crd takes precedence over loc.
            if 'crd' in p['plot']['title']:
                if 'pad' in p['plot']['title']['kwargs']:
                    # The pad property is available only in the set_title()
                    # method.
                    del p['plot']['title']['kwargs']['pad']
                ax.text(*p['plot']['title']['crd'],
                        the_title,
                        transform=ax.transAxes,
                        **p['plot']['title']['kwargs'])
            elif 'loc' in p['plot']['title']:
                ax.set_title(the_title,
                             loc=p['plot']['title']['loc'],
                             **p['plot']['title']['kwargs'])
            self.is_drawn['title'] = True

        #
        # Plotting: Annotation markers for spotted radionuclides
        #
        if re.search('(?i)rn|marker', plot_type):
            # Aliasing
            annots = p['plot']['annots']
            col_rn = cols['radionuclide']['nucl_data_new']
            col_nrg = cols['energy']['nucl_data_new']
            col_ep = cols['emission_probability']['nucl_data_new']
            col_hl = cols['half_life']['nucl_data_new']
            col_dm = cols['decay_mode']['nucl_data_new']
            col_flag = cols['flag']['nucl_data_new']
            nrg_lims = []
            ep_lims = []
            for win in annots['every']['cutoffs'].values():
                nrg_lims.append([float(nrg) for nrg in win['energy']])
                ep_lims.append([float(ep) for ep
                               in win['emission_probability']])

            #
            # Figure base name modification (4/4)
            # - Append the name of the annotation type to the base names of
            #   figure files.
            # - Use the bool is_finalize to avoid repetitive modifications
            #   when this function is called multiple times.
            #
            if is_finalize:
                out_fig_bname += '_{}'.format(annots['type'])

            #
            # Shade for energy-cutoff regions
            #
            if annots['every']['shade']['toggle']:
                cutoff_nrgs = [float(nrg) for nrg
                               in p['scout']['radionuclides']['cutoffs'][
                                   'energy']]
                # Lower cutoff energy region
                # Draw a shade from (x0=0, y0=0) only if the lower cutoff
                # energy is greater than zero.
                if cutoff_nrgs[0] > 0:
                    shade_llim_org = (0, 0)  # (x0, y0)
                    shade_llim_wth = cutoff_nrgs[0]
                    shade_llim_hgt = ax.get_ylim()[1]
                    rect_llim = patches.Rectangle(
                        shade_llim_org,
                        shade_llim_wth, shade_llim_hgt,
                        **annots['every']['shade']['kwargs'])
                    ax.add_patch(rect_llim)
                # Upper cutoff energy region
                # Draw a shade from (x0=cutoff_nrgs[1], y0=0) only if the upper
                # cutoff energy (cutoff_nrgs[1]) is smaller than the upper
                # x-axis limit.
                if cutoff_nrgs[1] < ax.get_xlim()[1]:
                    shade_ulim_org = (cutoff_nrgs[1], 0)
                    shade_ulim_wth = ax.get_xlim()[1]
                    shade_ulim_hgt = ax.get_ylim()[1]
                    rect_ulim = patches.Rectangle(
                        shade_ulim_org,
                        shade_ulim_wth, shade_ulim_hgt,
                        **annots['every']['shade']['kwargs'])
                    ax.add_patch(rect_ulim)

            #
            # Marker customization: User input-based
            #
            mrk_groups = ['dflt', 'g1', 'g2', 'combined']
            mrks_yml = {g: {} for g in mrk_groups}
            mrk_attrs = ['msymb', 'mfc', 'mec', 'mew', 'msz', 'alpha']
            for attr in mrk_attrs[1:]:
                mrks_yml['dflt'][attr] = annots['grouped']['defaults'][attr]
            # g1: User-specified markers
            mrks_yml['g1'] = self.set_markers(annots['grouped']['markers'],
                                              mrks_yml['dflt'])
            # g2: Spare markers
            _markers_g2 = list(Line2D.markers.keys())
            mrks_yml['g2']['msymb'] = [m2 for m2 in _markers_g2
                                       if m2 not in mrks_yml['g1']['msymb']]
            mrks_yml['combined']['msymb'] = (mrks_yml['g1']['msymb']
                                             + mrks_yml['g2']['msymb'])
            shortfall = (len(mrks_yml['combined']['msymb'])
                         - len(mrks_yml['g1']['msymb']))
            # g1 + g2: User-specified and spare markers
            for attr in mrk_attrs[1:]:
                mrks_yml['g2'][attr] = [mrks_yml['dflt'][attr]] * shortfall
                mrks_yml['combined'][attr] = (mrks_yml['g1'][attr]
                                              + mrks_yml['g2'][attr])

            #
            # Marker customization: Marker registry-based
            #
            # - A marker registry takes precedence over the markers defined
            #   at the user input file and the commands above.
            # - The purpose of a marker registry is to use consistent markers
            #   across plots of the same dataset with different energy ranges.
            #
            is_marker_registry = bool(
                os.path.exists(p['io']['lib']['marker_registry_fname_full']))
            if is_marker_registry:
                mrks_reg = {}
                rns = []
                mrks_def = []
                with open(p['io']['lib']['marker_registry_fname_full'], 'r',
                          encoding='utf8') as fh_inp:
                    for line in fh_inp.readlines():
                        if re.search(r'^\s*#', line) or re.search('^$', line):
                            continue
                        rn, mrk_def = [s.strip().strip('"') for s
                                       in re.split(r'\s*;\s*', line)]
                        rns.append(rn)
                        mrks_def.append(mrk_def)
                mrks_expanded = self.set_markers(mrks_def, mrks_yml['dflt'])
                for i, rn in enumerate(rns):
                    mrks_reg[rn] = {}
                    for attr in mrk_attrs:
                        mrks_reg[rn][attr] = mrks_expanded[attr][i]

            # Iterate over radionuclides.
            rns_uniq = list(df[col_rn].unique())
            for i, rn in enumerate(rns_uniq):
                #
                # !!! df_rn: Suspect (radionuclide)-wise DF
                #
                bool_idx_rn = df[col_rn] == rn
                df_rn = df[bool_idx_rn].copy()
                # Fallback for unspotted local maxima
                # - Unspotted local maxima will have NaN in their decay
                #   data energy column. Fill such NaN values with the
                #   corresponding spectrum energies.
                # - The energy annotations of spotted local maxima will then
                #   indicate the energies of nuclear data, whereas unspotted
                #   local maxima will be labeled with the actual spectrum
                #   energies.
                if is_spotting:
                    df_rn[cols[x]['nucl_data_new']].fillna(
                        cols[x]['spectrum'],
                        inplace=True)
                # ydata (cols[y]) can either be:
                # - an emission probability dataset for nuclear data plotting
                # - a count dataset for radiation spectrum plotting
                # ydata_eps (cols['emission_probability']), on the other hand,
                # is always:
                # - an emission probability dataset, in combination with xdata,
                #   for selective annotations in nuclear data or radiation
                #   spectrum plotting
                xdata = df_rn[cols[x][data_col_type]].copy()
                ydata = df_rn[cols[y][data_col_type]].copy()
                ydata_eps = df_rn[cols['emission_probability'][
                    'nucl_data_new']].copy()
                #
                # Sum up, if any, true coincidence summing energies
                # (TCS implies that the summing energies belong to
                # the same radionuclide) to be iterated through later
                # in annotation command blocks.
                # e.g. Ac-225
                # - 100.209 + 108.4 => 208.609
                # - 100.209 + 150.1 => 250.309
                # - ...
                #
                if is_spotting:
                    for idx, nrg in zip(xdata.index, xdata):
                        if re.search(r'([0-9.]+)\s*[+]\s*([0-9.]+)', str(nrg)):
                            nrgs_tcs = [float(n) for n
                                        in re.split(r'\s*[+]\s*', str(nrg))]
                            xdata[idx] = sum(nrgs_tcs)
                # Spotted radionuclides
                if re.search('[a-zA-Z]+-[0-9]+', rn):
                    # Convert the radionuclide string to the nuclide notation.
                    # - The \mathrm{} command makes, when encounters, the "m"
                    #   symbol of a nuclear isomer an upright character.
                    elem, mass_num = rn.split('-')
                    lab_rn = r'$^{\mathrm{%s}}$%s' % (mass_num, elem)
                # Local maxima without spotted radionuclides
                else:
                    lab_rn = str(rn)
                #
                # Annotation type: every
                # - Every local maximum is directly annotated with a label.
                #
                if re.search('(?i)every|both', annots['type']):
                    # !!! itn is used to set the y-coordinates of markers.
                    # !!! itn can either be ep or cnt. See the explanation
                    # "ydata (cols[y]) can either be:" above for details.
                    for idx, nrg_sum, itn, ep in zip(xdata.index, xdata,
                                                     ydata, ydata_eps):
                        # Skip if the radiation energy of interest exceeds
                        # the x-axis plotting range.
                        if (not p['plot']['xticks']['is_auto']
                                and not (xlim[0] <= nrg_sum <= xlim[1])):
                            continue
                        # Selectively annotate using the user-specified cutoff
                        # values of energy and emission probability.
                        is_cutoff = True
                        if ep != ep:  # TCS having NaN emission probability
                            ep = 0.0
                        for nrg_lim, ep_lim in zip(nrg_lims, ep_lims):
                            if ((nrg_lim[0] <= nrg_sum <= nrg_lim[1])
                                    and (ep_lim[0] <= ep <= ep_lim[1])):
                                is_cutoff = False
                                break
                        if is_cutoff:
                            continue
                        # >> Can be referenced from within the user input file
                        # - "nrg" differs from "nrg_sum" in that for TCS
                        #   energies, "nrg" contains an intact string of TCS
                        #   energies separated by a plus sign within that
                        #   string, whereas "nrg_sum" is a float and the sum
                        #   of TCS energies. See "Sum up, if any, ..."
                        #   and its "if is_spotting:" conditional for details.
                        # - The as-is string of "nrg" containing a plus sign
                        #   can be used to annotate the corresponding energy
                        #   point to emphasize that this local maximum is the
                        #   result of TCS.
                        nrg = df_rn.loc[idx, col_nrg]  # != nrg_sum
                        ep = df_rn.loc[idx, col_ep]
                        hl = df_rn.loc[idx, col_hl]
                        dm = df_rn.loc[idx, col_dm]
                        # <<
                        if isinstance(dm, str):
                            # Upright greek letters for decay mode
                            # (alpha, beta plus, and beta minus)
                            dm = re.sub('A', '\u03B1', dm)
                            dm = re.sub('B([+-]?)', '\u03B2$^{\\1}$', dm)
                        every_type = 'single'
                        # Make the energies of true coincidence summing whole
                        # numbers with rounding performed.
                        if is_spotting:
                            flag = df_rn.loc[idx, col_flag]
                            re_tcs = re.compile(
                                r'(?i)t(rue\s+)?c(oincidence\s+)?s(umming)?')
                            if re.search(re_tcs, str(flag)):
                                every_type = 'tcs'
                                _sep = re.sub(r'[0-9.]+(\s*[+]\s*)[0-9.]+',
                                              r'\1',
                                              nrg)
                                _nrgs = ['{:.0f}'.format(float(n)) for n
                                         in re.split(r'\s*[+]\s*', nrg)]
                                nrg = _sep.join(_nrgs)
                            else:
                                every_type = 'single'
                        # Iterate over each line under the 'every' key.
                        for line in annots['every'][every_type].values():
                            try:
                                lab_rn_nrgwise = eval(line['fmt'])
                            # Fallback for
                            # - Annihilation peak
                            # - Unspotted local maxima
                            except ValueError:  # As a result of eval()
                                _fback = annots['every'][every_type].values()
                                if len(_fback) == 1:
                                    lab_rn_nrgwise = '{:.0f}'.format(nrg_sum)
                                else:
                                    lab_rn_nrgwise = ''
                            # To reiterate, itn can either be ep or cnt.
                            crd_y = itn * line['offy'] if line['offy'] else itn
                            # Annotate each data point.
                            ax.text(nrg_sum, crd_y, lab_rn_nrgwise,
                                    **line['kwargs'])
                #
                # Annotation type: grouped
                # - Groups of local maxima beloning to specific radionuclides
                #   are labeled with respective markers, and the group
                #   information is displayed in the legend.
                #
                if re.search('(?i)grouped|both', annots['type']):
                    the_msymb = mrks_yml['combined']['msymb'][i]
                    the_mfc = mrks_yml['combined']['mfc'][i]
                    the_mec = mrks_yml['combined']['mec'][i]
                    the_mew = mrks_yml['combined']['mew'][i]
                    the_msz = mrks_yml['combined']['msz'][i]
                    the_alpha = mrks_yml['combined']['alpha'][i]
                    if (is_marker_registry
                            and rn in mrks_reg):
                        the_msymb = mrks_reg[rn]['msymb']
                        the_mfc = mrks_reg[rn]['mfc']
                        the_mec = mrks_reg[rn]['mec']
                        the_mew = mrks_reg[rn]['mew']
                        the_msz = mrks_reg[rn]['msz']
                        the_alpha = mrks_reg[rn]['alpha']
                    if not p['plot']['xticks']['is_auto']:
                        bool_idx = ((xdata >= xlim[0])
                                    & (xdata <= xlim[1]))
                        nrgs_in_range = xdata[bool_idx]
                        if not nrgs_in_range.empty:
                            xdata_gr = nrgs_in_range
                            ydata_gr = ydata[bool_idx]
                            ax.plot(xdata_gr, ydata_gr,
                                    linestyle='',
                                    marker=the_msymb,
                                    markerfacecolor=the_mfc,
                                    markeredgecolor=the_mec,
                                    markeredgewidth=the_mew,
                                    markersize=the_msz,
                                    alpha=the_alpha,
                                    label=lab_rn,
                                    # Allow markers to go beyond axes.
                                    clip_on=False)
                    else:
                        ax.plot(xdata_gr, ydata_gr,
                                linestyle='',
                                marker=the_msymb,
                                markerfacecolor=the_mfc,
                                markeredgecolor=the_mec,
                                markeredgewidth=the_mew,
                                markersize=the_msz,
                                alpha=the_alpha,
                                label=lab_rn,
                                clip_on=False)
            if (re.search('(?i)grouped|both', annots['type'])
                    and annots['grouped']['legend']['toggle']):
                handles, labels = ax.get_legend_handles_labels()
                if (len(handles) != 0
                        and annots['grouped']['legend']['order'] != 'as_is'):
                    is_reverse = bool(
                        annots['grouped']['legend']['order'] == 'descending')
                    handles, labels = self.sort_legend(
                        handles, labels,
                        is_reverse=is_reverse)
                ax.legend(handles, labels,
                          **annots['grouped']['legend']['kwargs'])

        #
        # Save the figure to files.
        #
        if not is_finalize:
            return
        is_gs = p['io']['ctrls']['pdf_postproc']['ghostscript']['toggle']
        is_pdfcrop = p['io']['ctrls']['pdf_postproc']['pdfcrop']['toggle']
        if p['io']['ctrls']['is_plot_test']:
            mt.show_warn('Running in a plot testing mode...')
            p['io']['ctrls']['is_plot'] = True
            p['io']['ctrls']['is_save_fig'] = True
            p['io']['ctrls']['fig_fmts'] = ['png']
            is_gs = False
            is_pdfcrop = False
        if p['io']['ctrls']['is_plot']:
            io.mk_dir(p['io']['out']['fig_path'])
            inkscape_exe = os.path.expandvars(
                p['io']['ctrls']['inkscape']['exe'])
            self.save_fig(fig,
                          p['io']['out']['fig_path'],
                          out_fig_bname,
                          p['io']['ctrls']['fig_fmts'],
                          dpi=p['io']['ctrls']['raster_dpi'],
                          inkscape_exe=inkscape_exe)
        if is_gs or is_pdfcrop:
            pdf_fname_full = '{}/{}.pdf'.format(p['io']['out']['fig_path'],
                                                out_fig_bname)
            gs_exe = os.path.expandvars(
                p['io']['ctrls']['pdf_postproc']['ghostscript']['exe'])
            gs_pdf_ver = p['io']['ctrls']['pdf_postproc']['ghostscript'][
                'pdf_ver']
            pdfcrop_exe = os.path.expandvars(
                p['io']['ctrls']['pdf_postproc']['pdfcrop']['exe'])
            self.run_pdf_postproc(pdf_fname_full,
                                  is_gs=is_gs,
                                  gs_exe=gs_exe,
                                  gs_pdf_ver=gs_pdf_ver,
                                  is_pdfcrop=is_pdfcrop,
                                  pdfcrop_exe=pdfcrop_exe)

    def save_fig(self, fig, out_path, out_bname, fmts,
                 dpi=300, inkscape_exe='inkscape.exe'):
        """Save an MPL figure in multiple formats.

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            An MPL Figure object.
        out_path : str
            The path to which figure files will be saved.
        out_bname : str
            The base name of figure files.
        fmts : list
            The formats of figure files.
        dpi : int, optional
            Raster figure resolution. The default is 300.
        inkscape_exe : str, optional
            A full-path Inkscape executable. The default is 'inkscape.exe'.

        Returns
        -------
        None.
        """
        # Generate the output directory if not exists.
        io.mk_dir(out_path)

        # Save figure files in user-designated file formats.
        out_bname_full = '{}/{}'.format(out_path, out_bname)
        is_svg = True if 'svg' in (fmt.lower() for fmt in fmts) else False
        for fmt in fmts:
            out_fname_full = '{}.{}'.format(out_bname_full, fmt)
            # All but .emf
            if not re.search('(?i)emf', fmt):
                fig.savefig(out_fname_full, dpi=dpi, bbox_inches='tight')
                io.show_file_gen(out_fname_full)
            # .emf via from .svg
            else:
                is_inkscape_exe_found = bool(os.path.exists(inkscape_exe))
                if not is_inkscape_exe_found:
                    inkscape_exe_on_environ_var = io.locate_exe(
                        '(?i)inkscape.*bin',
                        '(?i)inkscape[.]exe$')
                    if inkscape_exe_on_environ_var:
                        msg = ('The designated inkscape executable'
                               + f' [{inkscape_exe}] could not be located,\n'
                               + 'but its alternative'
                               + f' [{inkscape_exe_on_environ_var}] was found'
                               + ' in the path environment variable.'
                               + ' We fall back to this executable.')
                        mt.show_warn(msg)
                        inkscape_exe = inkscape_exe_on_environ_var
                        is_inkscape_exe_found = True
                if not is_inkscape_exe_found:
                    msg = ('The designated Inkscape executable '
                           + f' [{inkscape_exe}] could not be located;\n'
                           + '.emf rendering will be skipped.')
                    mt.show_warn(msg)
                    continue
                _svg = '{}.svg'.format(out_bname_full)
                if not is_svg:
                    fig.savefig(_svg, dpi=dpi, bbox_inches='tight')
                inkscape_exe = '"{}"'.format(inkscape_exe)
                _inkscape_cmd = [
                    inkscape_exe,
                    _svg,
                    '--export-filename={}'.format(out_fname_full),
                ]
                inkscape_cmd = ' '.join(_inkscape_cmd)
                subprocess.run(inkscape_cmd, shell=True, check=True)
                if not is_svg:
                    os.unlink(_svg)
                io.show_file_gen(out_fname_full,
                                 verb=f' generated using [{inkscape_exe}].')

    def run_pdf_postproc(self, pdf_fname_full,
                         is_gs=True, gs_exe='gswin64.exe', gs_pdf_ver=1.5,
                         is_pdfcrop=True, pdfcrop_exe='pdfcrop.exe'):
        """Postprocess a .pdf figure file.

        Parameters
        ----------
        pdf_fname_full : str
            The name of a PDF file to be postprocessed.
        is_gs : bool, optional
            If True, the size of the designated PDF file is reduced and/or
            the PDF file is reversioned using Ghostscript. Recommended for
            a PDF file generated by Matplotlib with pdf.fonttype = 42.
            The default is True.
        gs_exe : str, optional
            A full-path Ghostscript executable. The default is 'gswin64.exe'.
        gs_pdf_ver : float, optional
            The version you want the postprocessed PDF to have.
            The default is 1.5 (pdfTeX requirement).
        is_pdfcrop : bool, optional
            If True, the empty margins of the designated PDF file are cropped
            using pdfcrop. The default is True.
        pdfcrop_exe : str, optional
            A full-path pdfcrop executable. The default is 'pdfcrop.exe'.

        Returns
        -------
        None.
        """
        #
        # Argument validity inspection
        #
        if not os.path.exists(pdf_fname_full):
            msg = (f'[{pdf_fname_full}] not found;'
                   + ' run_pdf_postproc() will be skipped.')
            mt.show_warn(msg)
            return
        valid_gs_pdf_ver = [v / 10 for v in list(range(13, 18))]
        valid_gs_pdf_ver_str = ', '.join(map(str, valid_gs_pdf_ver))
        if gs_pdf_ver not in valid_gs_pdf_ver:
            msg = (f'gs_pdf_ver must be one of [{valid_gs_pdf_ver_str}].')
            raise ValueError(msg)

        #
        # File name construction
        #
        bname, ext = os.path.splitext(pdf_fname_full)
        _pdf_fname_full = '{}0{}'.format(bname, ext)  # Temporary .pdf storage

        #
        # PDF postprocessing (1/2)
        # Reduce the file size of .pdf using Ghostscript.
        #
        # Try to use the user-designated Ghostscript executable, if any.
        # If this is not found, search on the path environment variable.
        # If still not found, skip running Ghostscript.
        #
        is_gs_exe_found = bool(os.path.exists(gs_exe))
        if not is_gs_exe_found:
            gs_exe_on_environ_var = io.locate_exe('(?i)gs.*bin',
                                                  '(?i)gswin[0-9]+c[.]exe$')
            if gs_exe_on_environ_var:
                msg = (f'The designated pdfcrop executable [{gs_exe}]'
                       + ' could not be located,\nbut its alternative'
                       + f' [{gs_exe_on_environ_var}] was found'
                       + ' in the path environment variable.'
                       + ' We fall back to this executable.')
                mt.show_warn(msg)
                gs_exe = gs_exe_on_environ_var
                is_gs_exe_found = True
        if is_gs and not is_gs_exe_found:
            msg = (f'The designated Ghostscript executable [{gs_exe}]'
                   + ' could not be located;\n'
                   + '.pdf file size reduction will be skipped.')
            mt.show_warn(msg)
        elif is_gs and is_gs_exe_found:
            gs_exe = '"{}"'.format(gs_exe)  # A measure for blank spaces
            _gs_cmd = [
                gs_exe,
                '-dSAFER',
                '-dBATCH',
                '-dNOPAUSE',
                '-sDEVICE=pdfwrite',
                '-dCompatibilityLevel={}'.format(gs_pdf_ver),
                '-dSubsetFonts=true',
                '-dEmbedAllFonts=true',
                # Do not rotate the PDF file even if the height is greater
                # than the width, which can happen in figures where the
                # legends are placed outside the Axes.
                # https://ghostscript.com/docs/9.54.0/VectorDevices.htm
                '-dAutoRotatePages=/None',
                '-sOutputFile={}'.format(_pdf_fname_full),
                '-f {}'.format(pdf_fname_full),
            ]
            gs_cmd = ' '.join(_gs_cmd)
            subprocess.run(gs_cmd, shell=True, check=True)
            os.unlink(pdf_fname_full)
            os.rename(_pdf_fname_full, pdf_fname_full)
            io.show_file_gen(pdf_fname_full,
                             verb=f' file size reduced using [{gs_exe}].')

        #
        # PDF postprocessing (2/2)
        # Crop the empty margins of .pdf using pdfcrop. The executable locating
        # process is the same as that for Ghostscript.
        #
        is_pdfcrop_exe_found = bool(os.path.exists(pdfcrop_exe))
        if not is_pdfcrop_exe_found:
            pdfcrop_exe_on_environ_var = io.locate_exe('(?i)texlive',
                                                       '(?i)pdfcrop[.]exe$')
            if pdfcrop_exe_on_environ_var:
                msg = (f'The designated pdfcrop executable [{pdfcrop_exe}]'
                       + ' could not be located,\nbut its alternative'
                       + f' [{pdfcrop_exe_on_environ_var}] was found'
                       + ' in the path environment variable.'
                       + ' We fall back to this executable.')
                mt.show_warn(msg)
                pdfcrop_exe = pdfcrop_exe_on_environ_var
                is_pdfcrop_exe_found = True
        if is_pdfcrop and not is_pdfcrop_exe_found:
            msg = (f'The designated pdfcrop executable [{pdfcrop_exe}]'
                   + ' could not be located;\n'
                   + '.pdf margin cropping will be skipped.')
            mt.show_warn(msg)
        elif is_pdfcrop and is_pdfcrop_exe_found:
            # Fallback for a pdfcrop Perl script
            pdfcrop_exe = '"{}"'.format(pdfcrop_exe)
            if not re.search('(?i)[.]exe"?$', pdfcrop_exe):
                perl_exe_on_environ_var = io.locate_exe('(?i)perl',
                                                        '(?i)perl[.]exe$')
                if not perl_exe_on_environ_var:
                    msg = (f'You have designated a Perl script [{pdfcrop_exe}]'
                           + ' as the pdfcrop executable,\nbut it seems that'
                           + ' a Perl executable is unavailable in the path'
                           + ' environment variable.\n'
                           + '.pdf margin cropping will be skipped.')
                    mt.show_warn(msg)
                    return
                pdfcrop_exe = 'perl {}'.format(pdfcrop_exe)
            _pdfcrop_cmd = [
                pdfcrop_exe,
                '-margins "0 0 0 0"',
                '{} {}'.format(pdf_fname_full, _pdf_fname_full),
            ]
            pdfcrop_cmd = ' '.join(_pdfcrop_cmd)
            subprocess.run(pdfcrop_cmd, shell=True, check=True)
            os.unlink(pdf_fname_full)
            os.rename(_pdf_fname_full, pdf_fname_full)
            io.show_file_gen(pdf_fname_full,
                             verb=f' margin cropped using [{pdfcrop_exe}].')


if __name__ == '__main__':
    import mytoolkit as mt
    mt.show_warn('You are running me directly.')
    painter = Painter()
    painter.set_plot_style({})

else:
    try:
        from modules import mytoolkit as mt
        from modules import inpout
    except ModuleNotFoundError:
        import mytoolkit as mt
        import inpout
    io = inpout.InpOut()
