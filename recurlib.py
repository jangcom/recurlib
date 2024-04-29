#!/usr/bin/env python3
"""RecurLib: A recursion-based radionuclide library generator

Classes
-------
Recurlib()
    A class for recursion-based radionuclide library generation.
"""

import os
import sys
import time
import re
import copy
from urllib import request
import matplotlib.pyplot as plt
import pandas as pd

__author__ = 'Jaewoong Jang'
__copyright__ = 'Copyright (c) 2024 Jaewoong Jang'
__license__ = 'MIT License'
__version__ = '1.0.0'
__date__ = '2024-04-28'


class Recurlib():
    """A class for recursion-based radionuclide library generation.

    Attributes
    ----------
    radiat : dict
        A dictionary to hold short and long names of a spectrum radiation.
    lineage : dict
        A dictionary to hold a linear series of parent and daughter
        radionuclides.
    levs : dict
        A dictionary to hold the energy levels of radionuclides
        which will in turn be used to judge if their nuclear isomers
        can coexist in their decay chains.
    cols : dict
        A dictionary to hold the column names appearing in
        the nuclear data files and the corresponding column names
        specified by the user to be used in output DFs.
    df_rnlib : pandas.core.frame.DataFrame
        A radionuclide library DF containing progenitors designated by
        user input and their progeny recursively computed, with their decay
        data coupled.
    df_rnlib_xml : pandas.core.frame.DataFrame
        A DF essentially the same as df_rnlib except that the column names
        are modified with respect to .xml.

    Methods
    -------
    set_radiat(spectr_radiat)
        Populate the radiat attribute.
    set_cols(col_groups)
        Populate the cols attribute.
    get_rn_alias(rn, how='plain2lc')
        Return an alias of a radionuclide name.
    get_livechart_df(url_params, nucl_data_nonexist_fname_full,
                     decay_radiat_type_pair, is_verbose=False)
        Generate a nuclear data DF using the IAEA-NDS Live Chart web API.
    run_get_livechart_df(dat_fname_full, url_params,
                         nucl_data_nonexist_fname_full='',
                         decay_radiat_type_pair='',
                         is_verbose=False)
        get_livechart_df() wrapper.
    update_lineage(lineage, parent, daughter,
                   is_verbose=False)
        Update the lineage of a parent radionuclide.
    get_daughters(parent, nucl_data_path, nucl_data_nonexist_fname_full,
                  is_verbose=False)
        Return a list of all possible progeny of a parent radionuclide.
    set_progenitor(rn)
        Initialize a progenitor radionuclide.
    get_nrg_lev_end(df_rn_gams, nrg_lev_start,
                    is_verbose=False)
        Traverse through a gamma cascade given a start energy level.
    set_gams(rn, nucl_data_path,
             is_verbose=False)
        Set the end level energies of gamma data of a radionuclide.
    set_levs(rn, nucl_data_path,
             is_verbose=False)
        Set the energy levels of decay modes of a radionuclide.
    set_levs_energy_flattening(rn,
                               is_sort=True, is_sort_reverse=True)
        Flatten all possible energy levels of a radionuclide.
    set_levs_feasibility(self)
        Set the feasibilities of the decay modes of a radionuclide series.
    get_rnlib(p)
        Generate a radionuclide library by recursive computation.
    get_context(rnlib_bname, df_rnlib, df_col_type='nucl_data_new',
                is_verbose=False)
        Construct a context dict for Jinja rendering.
    run_recurlib(the_yml)
        Run recursive generation of a radionuclide library.
    """

    def __init__(self):
        """Initialize an object of the Recurlib class."""
        self.radiat = {}
        self.lineage = {}
        self.levs = {}
        self.cols = {}
        self.df_rnlib = None
        self.df_rnlib_xml = None

    def set_radiat(self, spectr_radiat):
        """Populate the radiat attribute.

        Parameters
        ----------
        spectr_radiat : str
            The type of radiation the spectrum of interest represents.

        Returns
        -------
        None.
        """
        # Radiation type validation
        allowed = ['alpha', 'gamma', 'beta minus']
        re_allowed = '|'.join(allowed)
        if not re.search(r'(?i)\b({})\b'.format(re_allowed), spectr_radiat):
            msg = ('The spectrum radiation has been set to be'
                   + f' [{spectr_radiat}];\nIt must be one of'
                   + f' [{re_allowed}]. Terminating the program.')
            mt.show_warn(msg)
            sys.exit()
        # Shorten the radiation type with respect to the IAEA-NDS Live Chart
        # of Nuclides.
        # Examples
        # - spl = 'beta minus' -> ['beta', 'minus']
        # - shortened = 'bm'
        # - spl = 'gamma' -> ['gamma']
        # - shortened = 'g'
        # - spl = 'alpha' -> ['alpha']
        # - shortened = 'a'
        spl = re.split(r'\s+', spectr_radiat)
        shortened = ''.join([s[0] for s in spl])
        self.radiat.update({'long': spectr_radiat.lower(),
                            'short': shortened})

    def set_cols(self, col_groups):
        """Populate the cols attribute.

        Parameters
        ----------
        col_groups : dict
            A dictionary holding key-val pairs of columns.

        Returns
        -------
        None.
        """
        # Initialization
        data_types = [
            'nucl_data_old',  # Original column names in nuclear data files
            'nucl_data_new',  # New column names of the nuclear data files
            'xml',  # Column names dedicated to .xml files
        ]
        self.cols.update({'nucl_data_to_rpt': {},
                          'rpt_to_xml': {}})
        # Iterate over column groups of data_types.
        # Examples
        # - The absence of the subkey "nucl_data_old" in a column group key,
        #   say "radionuclide", implies that there is no "radionuclide" column
        #   in the original nuclear data file.
        #   - k = 'radionuclide'
        #   - col_group = {
        #         'nucl_data_new': 'Radionuclide',
        #         'xml': 'isotope',
        #     }
        # - If, on the other hand, there is the subkey "nucl_data_old"
        #   associated to a column group key, for instance "energy", the column
        #   "energy" is expected to exist in the original nuclear data file.
        #   - k = 'energy'
        #   - col_group = {
        #         'nucl_data_old': 'energy',
        #         'nucl_data_new': 'Energy (keV)',
        #         'xml': 'energy',
        #     }
        for k, col_group in col_groups.items():
            #
            # Create column names for respective data types.
            #
            self.cols[k] = {}  # Initialization
            for data_type in data_types:
                if data_type in col_group:
                    # Examples
                    # - self.cols['energy'][nucl_data] = 'energy'
                    # - self.cols['energy'][rpt] = 'Energy (keV)'
                    # - self.cols['energy'][xml] = 'Energy'
                    self.cols[k].update({data_type: col_group[data_type]})
            #
            # Create maps for DF column renaming.
            #
            # (i) 'nucl_data_old' to 'nucl_data_new'
            # e.g. {'energy': 'Energy (keV)'}
            if ('nucl_data_old' in col_group
                    and 'nucl_data_new' in col_group):
                self.cols['nucl_data_to_rpt'].update(
                    {col_group['nucl_data_old']: col_group['nucl_data_new']})
            # (ii) 'nucl_data_new' to 'xml'
            # e.g. {'Energy (keV)': 'Energy'}
            if ('nucl_data_new' in col_group
                    and 'xml' in col_group):
                self.cols['rpt_to_xml'].update(
                    {col_group['nucl_data_new']: col_group['xml']})

    def get_rn_alias(self, rn,
                     how='plain2lc'):
        """Return an alias of a radionuclide name.

        Parameters
        ----------
        rn : str
            A radionuclide name to be aliased.
        how : str, optional
            An aliasing method. The default is 'plain2lc'.

        Returns
        -------
        rn_alias : str
            An aliased radionuclide name.
        """
        rn_alias = rn  # Default
        # (i) Plain to the Live Chart of Nuclides notation
        # e.g. Ac-225 -> 225ac, Tc-99m -> 99tc
        if how == 'plain2lc':
            rn_alias = re.sub(r'([a-z-A-Z]+)\-([0-9]+)m?',
                              r'\2\1',
                              rn_alias.lower())
        # (ii) Plain to code notation (Jinja templating)
        if how == 'plain2code':
            # e.g. Ac-225 -> AC225, Lu-177m -> LU177M
            rn_alias = re.sub('[-]', '', rn).upper()
        return rn_alias

    def get_livechart_df(self, url_params,
                         nucl_data_nonexist_fname_full,
                         decay_radiat_type_pair,
                         is_verbose=False):
        """Generate a nuclear data DF using the IAEA-NDS Live Chart web API.

        Parameters
        ----------
        url_params : dict
            A dictionary of the API parameters of IAEA-NDS Live Chart of
            Nuclides.
        nucl_data_nonexist_fname_full : str
            (An empty string toggles off the related commands.)
            The name of a file containing pairs of a radionuclide and decay
            radiation, where the radiation emission from the radionuclide
            does not have associated nuclear data in the ENSDF database.
            This function will create the file if it is not found in the
            user-designated directory, and add the dataless radionuclide-
            -radiation pairs to the file if a query to the Live Chart returns
            the error code 0 (0 means the queried nuclear data is unavailable).
        decay_radiat_type_pair : str
            (An empty string toggles off the related commands.)
            A pair of a radionuclide and decay radiation. This will be added
            to the file "nucl_data_nonexist_fname_full" if the error code 0 is
            encountered.
        is_verbose : bool, optional
            If True, an error code and its meaning will be displayed when
            issued. The default is False.

        Returns
        -------
        None or pandas.core.frame.DataFrame
            Failure of data retrieval from the IAEA-NDS Live Chart of Nuclides
            web API will return None.
            On the other hand, successful data retrieval will return a DF
            containing the nuclear data of interest.
        """
        #
        # Construct a data retrieval URL.
        #
        url_service = 'https://www-nds.iaea.org/relnsd/v1/data?'
        # e.g. ['fields'='decay_rads', 'nuclides'='225ac', 'rad_types'='a']
        url_params_listed = [f'{k}={v}' for k, v in url_params.items()]
        # e.g. 'fields=decay_rads&nuclides=225ac&rad_types=a'
        url_params_stringified = '&'.join(url_params_listed)
        url = url_service + url_params_stringified

        #
        # Read in and stringify the content of the URL, which is originally
        # binary data, for the subsequent error checking.
        #
        # The "User-Agent" key-val pair is prepared in two versions:
        # - as a list to be unpacked to two strings, which will then be passed
        #   to request.Request.add_header() as its positional arguments
        # - as a dict to be passed to pd.read_csv() as its positional argument
        #
        storage_opts = {'User-Agent': ''}
        storage_opts_listed = list(*storage_opts.items())
        req = request.Request(url)
        req.add_header(*storage_opts_listed)
        with request.urlopen(req) as content:
            content_stringified = str(content.read())

        #
        # Check if the data retrieval has failed.
        #
        error_codes = {
            # Rephrased those retrieved from:
            # www-nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html#error
            '0': 'Valid request, but no corresponding dataset is available.',
            '1': '"fields" unspecified.',
            '2': '"nuclides" required for use with "fields", but unspecified.',
            '3': '"fields" misspelled.',
            '4': '"parents" or "products" unspecified for fission yields.',
            '5': '"rad_types" invalid.',
            '6': 'Unknown error.',
        }
        re_error = re.compile(r'(?i)^b\'([0-6]{1})\\n\'$')  # e.g. b'6\n'
        is_error = bool(re.search(re_error, content_stringified))
        if is_error:
            err = re.sub(re_error, r'\1', content_stringified)  # Error code
            # If the error code 0 is returned, add the pair of the
            # radionuclide and the decay radiation to the file listing
            # radionuclide-radiation pairs having no associated nuclear data,
            # if the pair had not already been listed in the file.
            if (err == '0'
                    and nucl_data_nonexist_fname_full
                    and decay_radiat_type_pair):
                # Examine the registry if the pair is already listed in it.
                is_already_listed = False
                with open(nucl_data_nonexist_fname_full,
                          encoding='utf8') as fh_inp:
                    nonexist_pairs = [s.rstrip() for s in fh_inp.readlines()
                                      if not re.search('^$', s)]
                    for nonexist_pair in nonexist_pairs:
                        # If already listed in the registry, the pair needs
                        # not be added to it.
                        if re.search(nonexist_pair, decay_radiat_type_pair):
                            is_already_listed = True
                            break
                if not is_already_listed:
                    # Add the dataless pair to the registry. Remove, if any,
                    # duplicate pairs, and sort them.
                    nonexist_pairs.append(decay_radiat_type_pair)
                    nonexist_pairs_uniq = list(dict.fromkeys(nonexist_pairs))
                    nonexist_pairs_uniq_sorted = sorted(nonexist_pairs_uniq)
                    with open(nucl_data_nonexist_fname_full, 'w',
                              encoding='utf8') as fh_out:
                        for nonexist_pair in nonexist_pairs_uniq_sorted:
                            fh_out.write(f'{nonexist_pair}\n')
                if is_verbose:
                    msg = f'An error raised for: [{decay_radiat_type_pair}]'
                    mt.show_warn(msg)
            if is_verbose:
                mt.show_warn(error_codes[err])
            return None
        return pd.read_csv(url,
                           storage_options=storage_opts)

    def run_get_livechart_df(self, dat_fname_full, url_params,
                             nucl_data_nonexist_fname_full='',
                             decay_radiat_type_pair='',
                             is_verbose=False):
        """get_livechart_df() wrapper.

        Parameters
        ----------
        dat_fname_full : str
            A full-path name of an IAEA-NDS Live Chart of Nuclides data file.
        url_params : dict
            A dictionary of the API parameters of IAEA-NDS Live Chart of
            Nuclides.
        nucl_data_nonexist_fname_full : str, optional
            The name of a file containing pairs of a radionuclide and decay
            radiation, where the radiation emission from the radionuclide
            does not have associated nuclear data in the ENSDF database.
            See the docstring of get_livechart_df() for more details.
            The default is ''.
        decay_radiat_type_pair : str, optional
            A pair of a radionuclide and decay radiation. See the docstring of
            get_livechart_df() for more details.The default is ''.
        is_verbose : bool, optional
            If True, an error code and its meaning will be displayed when
            issued at get_livechart_df(). The default is False.

        Returns
        -------
        df_lc : pandas.core.frame.DataFrame
            A DF containing a dataset of IAEA-NDS Live Chart of Nuclides
            generated either via a local data file or the Live Chart API.
        """
        #
        # Check if the data file already exists.
        # => Is there is, use the already available file.
        # => If not, query the IAEA-NDS Live Chart server and save the
        #    fetched data to a file to the user-specified path for any
        #    future use.
        #
        is_decay_file = bool(os.path.exists(dat_fname_full))
        if is_decay_file:
            if is_verbose:
                print(f'The nuclear data file [{dat_fname_full}] found.')
            try:
                df_lc = pd.read_csv(dat_fname_full)
            except Exception:
                msg = (f'The nuclear data file [{dat_fname_full}] could'
                       + ' not be loaded correctly.\nPlease check if the'
                       + ' file conforms to the format of IAEA-NDS Live'
                       + ' Chart of Nuclides.\nTerminating the program.')
                mt.show_warn(msg)
                sys.exit()
        else:  # **Internet connection required**
            df_lc = self.get_livechart_df(url_params,
                                          nucl_data_nonexist_fname_full,
                                          decay_radiat_type_pair,
                                          is_verbose=is_verbose)
            if isinstance(df_lc, pd.DataFrame):
                # If the DF has been fetched from the IAEA-NDS Live Chart of
                # Nuclides server, save the DF to a file for future reuse.
                dat_dname = os.path.dirname(dat_fname_full)
                io.mk_dir(dat_dname, is_yn=False)
                df_lc.to_csv(dat_fname_full)
                io.show_file_gen(dat_fname_full)
        return df_lc

    def update_lineage(self, lineage, parent, daughter,
                       is_verbose=False):
        """Update the lineage of a parent radionuclide.

        Parameters
        ----------
        lineage : dict
            A dictionary for lineage construction; except a case when the
            positional argument "parent" is to be the progenitor of the
            lineage, this dictionary will always consists of nested
            dictionaries.
        parent : str
            A parent radionuclide of interest.
        daughter : str
            A daughter nuclide seeking for its parent.
        is_verbose : bool, optional
            If True, the lineage updating process will be displayed.
            The default is False.

        Returns
        -------
        None.
        """
        # If asked to do so, display the initial contents of lineage
        # construction components.
        # Examples of 'parent', 'daughter'
        # - 'Ac-225', 'Fr-221'
        # - 'Fr-221', 'At-217'
        # - 'At-217', 'Bi-213'
        # - ...
        if is_verbose:
            print('\n'
                  + mt.centering('update_lineage(lineage, parent, daughter)')
                  + '\n')
            the_comps = ['lineage', 'parent', 'daughter']
            the_comps_lengths = [len(s) for s in the_comps]
            lengthiest = max(the_comps_lengths)
        #
        # (i) Progenitor of the lineage
        # Each element in the scout > radionuclides > recursive list
        # in the user input file; e.g. Ac-225
        #
        if len(lineage) == 0:
            if is_verbose:
                print(mt.centering('*A decay chain progenitor*'))
                for comp in the_comps:
                    print(f'    - %-{lengthiest}s: %s' % (comp, eval(comp)))
            # At the very first call of this function, initialize the uppermost
            # dictionary with the parent radionuclide being a key and a pair of
            # its daughter, and an anonymous dictionary being the value.
            # e.g. lineage['Ac-225'] = {'Fr-221': {}}
            lineage[parent] = {daughter: {}}
        #
        # (ii) Progeny of the lineage
        # e.g. Fr-221, At-217, Bi-213, ...
        #
        else:
            # If asked to do so, display the contents of lineage construction
            # components.
            # Examples of 'parent', 'daughter'
            # - 'Fr-221', 'At-217'
            # - 'At-217', 'Bi-213'
            # - ...
            if is_verbose:
                print(mt.centering('**A decay chain progeny**'))
                for comp in ['lineage', 'parent', 'daughter']:
                    print(f'    - %-{lengthiest}s: %s' % (comp, eval(comp)))
            #
            # Recursively traverse the nested dictionaries until we find a key
            # that has the same name as the parent radionuclide.
            #
            # Base case
            # - branch == parent, meaning that we have arrived at the
            #   dictionary to which the pair of the daughter nuclide and
            #   an anonymous dictionary will be added.
            #
            # Recursive case
            # - branch != parent, and
            #   - len(lineage[branch]) >= 1, meaning that there is a nested
            #     dictionary down to the current level.
            #
            # Example: Ac-225
            # - Conditions
            #   - lineage = {'Ac-225': {'Fr-221': {}}}
            #   - parent = 'Fr-221'
            #   - daughter = 'At-217'
            # 1. "branch: 'Ac-225'" is not "parent: 'Fr-221'".
            #    As the base case has not been met, the program enters into
            #    the else conditional.
            # 2. The else conditional would be True, as there is the nested
            #    dictionary {'Fr-221': {}} under lineage['Ac-225']:
            #    len(lineage['Ac-225']) == len({'Fr-221': {}}): 1 >= 1
            # 3. The function is recursively called with
            #    lineage['Ac-225'] == {'Fr-221': {}}.
            # 4. Conditions
            #    - lineage = {'Fr-221': {}}
            #    - parent = 'Fr-221'
            #    - daughter = 'At-217'
            # 5. branch: 'Fr-221' is equal to parent: 'Fr-221'.
            #    The base case has now been satisfied, executing:
            #    lineage['Fr-221'].update({'At-217': {}}), which would yield
            #    'Fr-221': {'At-217': {}}
            #
            for branch in lineage.keys():
                if is_verbose:
                    branch_expl = f'        - branch (lineage key): {branch}'
                    print(branch_expl)
                if branch == parent:  # Base case
                    if is_verbose:
                        print(f'{branch_expl} == parent: {parent}')
                    #
                    # - Note that we need to use update() rather the equals
                    #   sign below (e.g. lineage[branch] = {daughter: {}}),
                    #   otherwise lineage[branch] would be initialized if it
                    #   has more than two daughter radionuclides.
                    # - Example: Bi-213 having the daughters Tl-209 and Po-213
                    #   lineage = {'Bi-213': {'Tl-209': {'Pb-209': ...}}}
                    #   Assume that the nesting of 'Tl-209' has been completed,
                    #   and the current daughter is 'Po-213'. When 'Po-213'
                    #   could locate 'Bi-213' as its parent, the command
                    #   lineage[branch] = {daughter: {}} would result in
                    #   lineage['Bi-213'] = {'Po-213: {}}, intializing the
                    #   anonymous dictionary bound to lineage['Bi-213'] and
                    #   hence removing the nested anonymous dictionary
                    #   {'Tl-209': {'Pb-209': ...}}.
                    #
                    lineage[branch].update({daughter: {}})
                    break
                else:
                    #
                    # - Without the conditional len(lineage[branch]) >= 1,
                    #   an empty nested dictionary {} would also be passed to
                    #   a recursive call as the "lineage" positional argument.
                    # - Remember that an empty lineage dictionary is the sign
                    #   of the progenitor of the lineage; see the beginning
                    #   part of this function. This would execute the command
                    #   lineage[parent] = {daughter: {}}, and result in one
                    #   or more additional and unintended progenitors.
                    #
                    if len(lineage[branch]) >= 1:
                        if is_verbose:
                            print('Recursively calling update_lineage()'
                                  + ' with lineage[branch],'
                                  + ' or {},'.format(lineage[branch])
                                  + ' as lineage...')
                        self.update_lineage(lineage[branch],
                                            parent, daughter,
                                            is_verbose=is_verbose)
        if is_verbose:
            print(f'Updated lineage: {lineage}')

    def get_daughters(self, parent,
                      nucl_data_path, nucl_data_nonexist_fname_full,
                      is_verbose=False):
        """Return a list of all possible progeny of a parent radionuclide.

        Parameters
        ----------
        parent : str
            A parent radionuclide of interest.
        nucl_data_path : str
            A directory containing nuclear data files.
        nucl_data_nonexist_fname_full : str
            The name of a file containing pairs of a radionuclide and decay
            radiation, where the radiation emission from the radionuclide
            does not have associated nuclear data in the ENSDF database.
        is_verbose : bool, optional
            If True, the unwinding process of recursion will be displayed.
            The default is False.

        Returns
        -------
        daughters : list
            A list of all possible progeny of the parent radionuclide.
            Duplicate daughter nuclides can be included if:
            (i) branching decay is involved in any stage of the decay
                of a parent radionuclide, and incidentally the same nuclides
                are generated through different branching paths.
            (ii) multiple parents have been specified in the user input file,
                 and one or more daughter nuclides of each parent radionuclide
                 can incidentally appear in the decay stage of other parents.
            As this function involves recursion, duplicate daughter nuclidess,
            if any, should and will be removed outside of this function.
        """
        #
        # Synopsis
        #
        # Assume that this function has been called from outside with the
        # string 'Ac-225' passed as the positional argument (there will be
        # some cases this function is invoked internally; see the number 3
        # below).
        #
        # 1. The string 'Ac-225' is converted to '225ac' to conform to the
        #    the web API syntax of the IAEA-NDS Live Chart of Nuclides.
        # 2. Query all possible types of radiation emission of Ac-225 to
        #    the Live Chart web API server, and for existing datasets,
        #    retrieve a list of the resulting daughter nuclides, no matter
        #    the associated branching fractions.
        # 3. Call this function with each of the collected daughter nuclides
        #    passed as the "parent" positional argument, and repeat such
        #    recursive calls until no daughter nuclide is retrieved; namely,
        #    the base case for the recursion to terminate is an empty list of
        #    daughter nuclides. Taking Ac-225 as an example, the recursion will
        #    end on 'Tl-205' as this nuclide is stable and hence has no
        #    daughter.
        #

        #
        # Convert the nuclide notation with respect to the Live Chart web API
        # syntax. Note that to conform to the syntax, the "m" symbol of
        # a nuclear isomer, if any, is dropped. For example:
        # - Ac-225 (RecurLib) to 225ac (Live Chart web API)
        # - Tc-99m (RecurLib) to 99tc (Live Chart web API)
        #
        parent_lc = self.get_rn_alias(parent, how='plain2lc')

        #
        # Examine the nuclear data of the parent radionuclide of interest
        # if any of the radiation types below is emitted as a result of its
        # decay. If so, collect the names of the resulting daughter nuclides.
        #
        radiat_types = [  # Values of the Live Chart rad_types parameter
            'a',  # Alpha
            'bp',  # Beta plus
            'bm',  # Beta minus
            'e',  # Auger or conversion electron
            'g',  # Gamma ray
            'x',  # X-ray
        ]
        # **Identified daughters will be tallied to the "daughters" list.**
        daughters = []
        if is_verbose:
            func_name_centered = mt.centering(
                'get_daughters(parent, nucl_data_path,'
                + ' nucl_data_nonexist_fname_full)')
            msg = ('\n'
                   + func_name_centered
                   + '\n\nUnder a new local namespace for this call\n'
                   + '              "parent": [{}]\n'.format(parent)
                   + '   Initial "daughters": [{}]\n'.format(
                       ', '.join(daughters)))
            print(msg)
        # Energy flattening of the parent radionuclide in question:
        # Preprocessing for possible decay mode inspection
        self.set_levs_energy_flattening(parent)
        for radiat_type in radiat_types:  # 'a', 'bp', 'bm', ..., 'x'
            #
            # Check if the pair of the radionuclide and the decay radiation is
            # included in the registry for nonexistent nuclear data.
            # => If included, skip the current iteration run as the radiation
            #    in question is not emitted as a result of the decay of the
            #    parent radionuclide, and there is no such nuclear data file
            #    as well.
            #
            decay_radiat_type_pair = '{}_{}'.format(parent, radiat_type)
            is_nonexistent = False
            with open(nucl_data_nonexist_fname_full) as fh_inp:
                for pair in fh_inp.readlines():
                    if re.search(decay_radiat_type_pair, pair):
                        is_nonexistent = True
                        break
            if is_nonexistent:
                if is_verbose:
                    msg = (f'The radionuclide [{parent}] does not have nuclear'
                           + f' data for the radiation [{radiat_type}].\n'
                           + 'Daughter identification at this pair will be'
                           + ' skipped.')
                    mt.show_warn(msg)
                continue
            #
            # Generate a parent DF using an existing nuclear data file
            # or, if unavailable, via the IAEA-NDS Live Chart of Nuclides.
            #
            decay_fname_full = '{}/{}/{}.csv'.format(nucl_data_path,
                                                     parent,
                                                     decay_radiat_type_pair)
            url_params = {
                'fields': 'decay_rads',
                'nuclides': parent_lc,
                'rad_types': radiat_type,
            }
            df_p = self.run_get_livechart_df(  # df_p: parent DF
                decay_fname_full, url_params,
                nucl_data_nonexist_fname_full=nucl_data_nonexist_fname_full,
                decay_radiat_type_pair=decay_radiat_type_pair,
                is_verbose=is_verbose)
            # df_p will be "None" on data retrieval failure.
            if isinstance(df_p, pd.DataFrame):
                # Remember that at this point, we are within the loop of
                # decay radiation types. From here, we will enter deeper
                # layer of iteration: A group of different daughter nuclides
                # belonging to the pair of the current radionuclide and
                # its decay radiation.
                # Example:
                # - Bi-213 either alpha-decays to Tl-209 or beta-decays to
                #   Po-213. Each of these decay modes is followed by gamma
                #   decay:
                #   (i) Gamma decay from the excited state of Tl-209 and
                #   (ii) Gamma decay from the excited state of Po-213,
                #   both of which are associated with the pair of Bi-213 and
                #   gamma radiation in conventional nuclear data.
                #   (therefore, the respective gamma rays are actually those
                #   of the daughter radionuclides, but the convention is to
                #   attribute the gamma rays to the parent radionuclide.)
                # Additionally, take this as an opportunity to reconstruct
                # the names of daughter nuclides with respect to the notation
                # of RecurLib;
                # e.g. 225ac to 'Ac-225'
                df_p['d_a'] = df_p['d_z'] + df_p['d_n']
                df_p['d_rn'] = df_p['d_symbol'] + '-' + df_p['d_a'].astype(str)
                candidates_uniq = df_p['d_rn'].unique().tolist()
                for daughter in candidates_uniq:
                    #
                    # Skip if the daughter and parent nuclides are the same
                    # nuclide.
                    #
                    # **Without this conditional, the recursion will not
                    # be able to reach the base case "len(daughters) == 0"
                    # as there will always be a daughter that will be passed
                    # to the recursion call after this conditional.**
                    #
                    # Such cases take place when the numbers of protons and
                    # neutrons of a daughter remain unchanged after its
                    # decay. Examples include:
                    # (i) Isomeric transition of a nuclear isomer (not to be
                    # confused with gamma decay, which occurs in the wake of
                    # preceding alpha, beta plus, electron capture, or beta
                    # minus decay and hence the resulting daughter nuclide
                    # differs from the parent)
                    # (ii) Internal conversion of an excited state
                    # (iii) Emission of an Auger or conversion electron, or
                    # emission of the subsequent characteristic X-rays
                    #
                    # A more detailed example: Assume that 'Tc-99' has been
                    # passed to this function (possibly identified as a
                    # daughter of 'Mo-99') as the "parent" positional argument,
                    # and the current decay radiation type of the loop is 'g'.
                    # The daughter of 'Tc-99' will then be 'Tc-99', which will
                    # be passed to the recursive call below, and so on.
                    # This will obviously lead to an infinite loop.
                    #
                    if daughter == parent:
                        continue
                    #
                    # Tally the identified daughter nuclide to the daughters
                    # list if and only if it is not already in the list.
                    #
                    # This conditional is necessary as different types of
                    # decay radiation (remember that we are now iterating over
                    # the radiat_types) can lead to the same daughter
                    # nuclide, particularly for those emitted in the wake of
                    # other decay modes.
                    #
                    # For example, gamma radiation of various energies is
                    # emitted as secondary radiation following the alpha
                    # decay of Ac-225, and both the alpha and gamma datasets
                    # will specify Fr-221, which is the product of Ac-225
                    # alpha decay, as their resulting daughter nuclide.
                    #
                    if daughter not in daughters:
                        daughters.append(daughter)
                        # Update the parent-daughter decay relation.
                        self.update_lineage(self.lineage, parent, daughter,
                                            is_verbose=is_verbose)
                    #
                    # Add the parent-daughter relation information
                    # to the levs dictionary.
                    #
                    # (i) parent: Add up its daughter information.
                    p_list_key = 'parents'
                    d_list_key = 'daughters'
                    if d_list_key not in self.levs[parent]:
                        self.levs[parent][d_list_key] = []
                    if daughter not in self.levs[parent][d_list_key]:
                        self.levs[parent][d_list_key].append(daughter)
                    # Key reorganization: If the parent radionuclide also has
                    # its parents key, place it before the daughters key.
                    if p_list_key in self.levs[parent]:
                        self.levs[parent] = {
                            p_list_key: self.levs[parent].pop(p_list_key),
                            d_list_key: self.levs[parent].pop(d_list_key),
                            **self.levs[parent],
                        }
                    # Key reorganization: Place the daughters key at the
                    # beginning.
                    else:
                        self.levs[parent] = {
                            d_list_key: self.levs[parent].pop(d_list_key),
                            **self.levs[parent],
                        }
                    # (ii) daughter: Add up its parent information.
                    if daughter not in self.levs:
                        self.levs[daughter] = {}
                    if p_list_key not in self.levs[daughter]:
                        self.levs[daughter][p_list_key] = []
                    if parent not in self.levs[daughter][p_list_key]:
                        self.levs[daughter][p_list_key].append(parent)
                    # Key reorganization: Place the parents key at the
                    # beginning.
                    self.levs[daughter] = {
                        p_list_key: self.levs[daughter].pop(p_list_key),
                        **self.levs[daughter],
                    }
                    #
                    # Memorize the energy levels of a daughter resulting from
                    # the decay of its parent, which will be used to
                    # - validate the energy level feasibility of the daughter
                    # - judge if the nuclear isomer of the daughter coexists.
                    #   A nuclear isomer of a daughter nuclide can coexist if
                    #   the decay of its parent leads to certain energy levels
                    #   of the daughter nuclide that represent an isomer state.
                    #
                    # Steps
                    # 1. Retrieve the energy levels, if any, of the
                    #    daughter nuclide inherited from its parent.
                    # 2. Traverse the gamma transitions of the daughter
                    #    nuclide and generate a list of its permissible
                    #    energy levels.
                    #
                    # Step 1
                    # 'daughter_level_energy' is the name of a column in
                    # a Live Chart-fetched nuclear data file.
                    if 'daughter_level_energy' in df_p.columns:  # p: parent
                        # Condition (i): Probable energy levels of the parent
                        bool_idx_p_nrg_lev = df_p['p_energy'].isin(
                            self.levs[parent]['energy_levels_flattened'])
                        # Condition (ii): Daughter data correspond to the
                        # current daughter in question
                        bool_idx_d_rn = df_p['d_rn'] == daughter  # d: daughter
                        # Decay modes of the parent radionuclide producing
                        # the daughter nuclide in question
                        # e.g. Ac-225 --a--> Fr-221
                        p_decays = df_p.loc[bool_idx_p_nrg_lev & bool_idx_d_rn,
                                            'decay'].to_list()
                        d_levs = df_p.loc[bool_idx_p_nrg_lev & bool_idx_d_rn,
                                          'daughter_level_energy'].to_list()
                        p_bequest_key = f'from_{parent}'
                        if p_bequest_key not in self.levs[daughter]:
                            self.levs[daughter][p_bequest_key] = {}
                        self.levs[daughter][p_bequest_key].update(
                            {'decay_modes': p_decays,
                             'energy_levels': d_levs})
                    # Step 2
                    self.set_gams(daughter, nucl_data_path)
                    self.set_levs(daughter, nucl_data_path)
        if is_verbose:
            print('Identified "daughters": [{}]'.format(', '.join(daughters)))

        #
        # Recursion
        #
        # Base case
        # - len(daughters) == 0, meaning that there is no daughter nuclide.
        #
        # Recursive case
        # - len(daughters) >= 1, meaning that there is at least one nuclide
        #   identified as a daughter nuclide.
        #
        # Example: Ac-225
        # - Ac-225 decay chain can be described as:
        #   (1) Ac-225 --a--> Fr-221 --a--> At-217 --a--> Bi-213
        #   (2a) Bi-213 --a--> Tl-209 --bm--> Pb-209
        #   (2b) Bi-213 --bm--> Po-213 --a--> Pb-209
        #   (3) Pb-209 --bm--> Bi-209 (--a--> Tl-205)
        # - The decay scheme of Bi-209 is enclosed with a pair of parentheses
        #   as Bi-209 has a physical half-life of 2.01e19 y, which is long
        #   enough to make it a practically stable nuclide.
        # - Note from (2a) and (2b) that Bi-213 decays to its granddaughter
        #   Pb-209 through either beta minus followed by alpha or the other
        #   way round, effectively emitting a pair of alpha and beta minus
        #   particles in one series of Ac-225 decay event.
        #
        # The expected scenario is as follows:
        # 1. This function is invoked from outside, with the string 'Ac-225'
        #    passed as the positional argument "parent".
        # 2. An anonymous list ['Fr-221'] will be added to the daughters list:
        #    daughters = ['Fr-221']
        # 3. Since the recursive condition "len(daughters) >= 1" is met,
        #    the element 'Fr-221' will be passed to a recursive call of this
        #    function as the positional argument "parent".
        #    Note that at this point, the first invocation of this function
        #    and therefore its local namespace remains alive and is stacked
        #    up in the memory.
        # 4. The recursive call with 'Fr-221' will result in
        #    daughters = ['At-217'] and invoke a next call with 'At-217'.
        # 5. The recursive call with 'At-217' will result in
        #    daughters = ['Bi-213'] and invoke a next call with 'Bi-213'.
        # 6. The recursive call with 'Bi-213' will result in
        #    daughters = ['Tl-209', 'Po-213'] and invoke a next call with
        #    'Tl-209'.
        #    **Note that 'Po-213' will be explored when we are done with
        #    'Tl-209' and its progeny.**
        # 7. The recursive call with 'Tl-209' will result in
        #    daughters = ['Pb-209'] and invoke a next call with 'Pb-209'.
        # 8. The recursive call with 'Pb-209' will result in
        #    daughters = ['Bi-209'] and invoke a next call with 'Bi-209'.
        # 9. The recursive call with 'Bi-209' will result in
        #    daughters = ['Tl-205'] and invoke a next call with 'Tl-205'.
        # 10a. The recursive call with 'Tl-205' will result in
        #      daughters = [], satisfying the base case
        #      "len(daughters) == 0".
        # 10b. This recursive call will be the first one, out of the many of
        #      its predecessors, to arrive at the statement "return daughters".
        # 10c. Now is the time for the recursive calls starting from 'Tl-209'
        #      to be unwinded back out.
        #      Where were we when we dove into the base case-met recursive
        #      call?
        #      We were right after the plus-equals sign which is meant to
        #      add up all the daughter nuclides into the list "daughters":
        #          daughters += get_daughters(parent,
        #                                     nucl_data_path,
        #                                     nucl_data_nonexist_fname_full)
        #      The effect of unwinding is illustrated below.
        #          daughters += []
        #          daughters += ['Tl-205']
        #          daughters += ['Bi-209'] + ['Tl-205']
        #          daughters += ['Pb-209'] + ['Bi-209'] + ['Tl-205']
        # 11. Remember that 'Tl-209' was where we left off, which is the
        #     parent of 'Pb-209' and the first daughter of 'Bi-213', and has
        #     a younger sister 'Po-213'. Since the series of recursive calls
        #     starting from 'Tl-209' has ended, we now resume the iteration
        #     from the second element of ['Tl-209', 'Po-213'], namely 'Po-213'.
        # 12. The recursive call with 'Po-213' will result in
        #     daughters = ['Pb-209'] and invoke a next call with 'Pb-209'.
        # 13. The recursive call with 'Pb-209' will result in
        #     daughters = ['Bi-209'] and invoke a next call with 'Bi-209'.
        # 14. The recursive call with 'Bi-209' will result in
        #     daughters = ['Tl-205'] and invoke a next call with 'Tl-205'.
        # 15a. The recursive call with 'Tl-205' will result in
        #      daughters = [], satisfying the base case
        #      "len(daughters) == 0".
        # 15b. The rest is the same as the end of the recursive calls starting
        #      from 'Pb-209'; the effect of unwinding is illustrated below.
        #          daughters += []
        #          daughters += ['Tl-205']
        #          daughters += ['Bi-209'] + ['Tl-205']
        #          daughters += ['Pb-209'] + ['Bi-209'] + ['Tl-205']
        # 16a. As all of the elements of 'Bi-213', or ['Pb-209', 'Po-213'],
        #      have been iterated through, the program will arrive at the
        #      subsequent return statement, returning the daughters list
        #      to its previous recursive call.
        #          (from the 'Tl-209' line)
        #          daughters += ['Pb-209', 'Bi-209', 'Tl-205']
        #          (from the 'Po-213' line)
        #          daughters += ['Pb-209', 'Bi-209', 'Tl-205']
        #          The two lists will then be concatenated into one:
        #          daughters += ['Pb-209', 'Bi-209', 'Tl-205',
        #                        'Pb-209', 'Bi-209', 'Tl-205']
        # 16b. The daughters ['Pb-209', 'Bi-209', 'Tl-205', 'Pb-209', 'Bi-209',
        #      'Tl-205'] will now be carried back into the previous recursive
        #      call at the right-hand side of
        #      "daughters += get_daughters(daughters_as_parent,
        #                                  nucl_data_path,
        #                                  nucl_data_nonexist_fname_full,
        #                                  is_verbose=is_verbose)".
        # 17. The rest is simply a process of unwinding back up to the first
        #     recursive call; the effect of unwinding is illustrated below.
        #         daughters += ['Tl-209', 'Po-213',
        #                       'Pb-209', 'Bi-209','Tl-205',
        #                       'Pb-209', 'Bi-209','Tl-205']
        #         daughters += ['Bi-213', 'Tl-209', 'Po-213',
        #                       'Pb-209', 'Bi-209', 'Tl-205',
        #                       'Pb-209', 'Bi-209', 'Tl-205']
        #         daughters += ['At-217',
        #                       'Bi-213', 'Tl-209', 'Po-213',
        #                       'Pb-209', 'Bi-209', 'Tl-205',
        #                       'Pb-209', 'Bi-209', 'Tl-205']
        #         Remember that we had daughters = ['Fr-221'] when the
        #         function was called from outside with 'Ac-225' as the
        #         "parent" positional argument:
        #         ['Fr-221'] += ['At-217',
        #                        'Bi-213', 'Tl-209', 'Po-213',
        #                        'Pb-209', 'Bi-209', 'Tl-205',
        #                        'Pb-209', 'Bi-209', 'Tl-205']
        #         The final daughters list will therefore be:
        #         daughters = ['Fr-221', 'At-217',
        #                      'Bi-213', 'Tl-209', 'Po-213',
        #                      'Pb-209', 'Bi-209', 'Tl-205',
        #                      'Pb-209', 'Bi-209', 'Tl-205']
        #     Note that there are two groups of ['Pb-209', 'Bi-209', 'Tl-205']
        #     in the daughters list. The first group originates from the
        #     series of recursive calls starting from 'Tl-209', which is the
        #     product of the alpha decay of 'Bi-213'. The second group, on the
        #     other hand, has been derived from the the successive recursive
        #     calls starting from 'Po-213', which is the product of the beta
        #     minus decay of 'Bi-213'.
        # 18. Now with the final daughters list, containing some duplicates as
        #     a result of the branching decay of 'Bi-213', the last alive call
        #     of this function is finally terminated and returns all possible
        #     progeny nuclides of 'Ac-225'.
        #     Note that the duplicate nuclides should and will be removed
        #     outside this function.
        #

        #
        # **We cannot iterate directly over the "daughters" list in a loop
        # where the "daughters" list itself will be modified, in which case
        # we will fall into an infite loop. Instead, create a new list having
        # exactly the same elements as "daughters" and run the loop with this
        # new list. Also note that we must not use a simple equals sign to
        # create a copy of the "daughters" list, as this would assign the
        # reference, rather than the content, of the "daughters" list to the
        # new list. A list comprehension has therefore been used here.**
        #
        daughters_as_parents = [d for d in daughters]
        if daughters:
            for daughters_as_parent in daughters_as_parents:
                daughters += self.get_daughters(daughters_as_parent,
                                                nucl_data_path,
                                                nucl_data_nonexist_fname_full,
                                                is_verbose=is_verbose)
        if is_verbose:
            print('Returning "daughters": [{}]'.format(', '.join(daughters)))
        return daughters

    def set_progenitor(self, rn):
        """Initialize a progenitor radionuclide.

        Parameters
        ----------
        rn : str
            A progenitor, namely a radionuclide designated at the user input
            file. Two variants exist:
              (i) A progenitor with one or more of its energy levels specified
              together; e.g. 'Nb-92m;135.5'
              The specified energy levels will be registered to the levs
              dictionary.
              (ii) A progenitor with its energy level omitted; e.g. 'Mo-99'
            In either case, this function will return the name of
            the radionuclide, with the specified energy levels and
            the potential "m" symbol, if any, dropped.

        Returns
        -------
        rn : str
            A progenitor without an "m" symbol.
        """
        #
        # (i) A progenitor with one or more of its energy levels specified
        # together; e.g. 'Nb-92m;135.5'
        #
        re_sep = re.compile(r'(?i)\s*;\s*')
        if re.search(re_sep, rn):
            spl = re.split(re_sep, rn)
            rn = spl[0]
            nrg_levs = [float(nrg_lev) for nrg_lev in spl[1:]]
        #
        # (ii) A progenitor with its energy level omitted; e.g. 'Mo-99'
        #
        else:
            nrg_levs = [0]  # 0 keV: The ground state
        #
        # Nuclear isomer handling
        # Once identified as a nuclear isomer, remove the trailing "m"
        # symbol for compatibility with decay and level data files and
        # the levs dictionary.
        #
        re_isomer = re.compile('(?i)m$')
        is_isomer_progenitor = bool(re.search(re_isomer, rn))
        rn = re.sub(re_isomer, '', rn)
        if rn not in self.levs:
            self.levs[rn] = {}
        # The "is_isomer_progenitor" key itself is required; both True and
        # False have respective roles.
        self.levs[rn]['is_isomer_progenitor'] = is_isomer_progenitor
        # A temporary key-val pair for nuclear isomer screening of
        # a user-designated progenitor; see set_levs_feasibility() for details.
        if is_isomer_progenitor:
            self.levs[rn]['energy_levels_isomer_progenitor'] = nrg_levs
        #
        # Associate the determined energy levels to the levs dictionary of
        # the progenitor in question.
        #
        if rn not in self.levs:
            self.levs[rn] = {}
        if 'from_user_input' not in self.levs[rn]:
            self.levs[rn]['from_user_input'] = {}
        if 'energy_levels' not in self.levs[rn]['from_user_input']:
            self.levs[rn]['from_user_input']['energy_levels'] = []
        # Aliasing
        user_inp_nrg_levs = self.levs[rn]['from_user_input']['energy_levels']
        for nrg_lev in nrg_levs:
            if nrg_lev not in user_inp_nrg_levs:
                user_inp_nrg_levs.append(nrg_lev)
        return rn

    def get_nrg_lev_end(self, df_rn_gams, nrg_lev_start,
                        is_verbose=False):
        """Traverse through a gamma cascade given a start energy level.

        Parameters
        ----------
        df_rn_gams : pandas.core.frame.DataFrame
            A DF containing gamma data of a radionuclide of interest.
        nrg_lev_start : float
            A start energy level.
        is_verbose : bool, optional
            If True, the unwinding process of recursion will be displayed.
            The default is False.

        Returns
        -------
        nrgs_lev_end_tally : list
            A tallied list of end energy levels.
        """
        # **Identified end level energies will be tallied to the
        # nrgs_lev_end_tally list.**
        nrgs_lev_end_tally = []
        if is_verbose:
            func_name_centered = mt.centering(
                'get_nrg_lev_end(df_rn_gams, nrg_lev_start)')
            msg = ('\n'
                   + func_name_centered
                   + '\n\nUnder a new local namespace for this call\n'
                   + '               "nrg_lev_start": {}'.format(
                       nrg_lev_start))
            print(msg)

        #
        # Find the end level energies, if any, corresponding to the given
        # start level energy (sle).
        #
        bool_idx_sle = ((df_rn_gams['sle_llim'] <= nrg_lev_start)
                        & (df_rn_gams['sle_ulim'] >= nrg_lev_start))
        nrgs_lev_end = df_rn_gams.loc[bool_idx_sle,
                                      'end_level_energy'].to_list()

        #
        # Recursive case (i)
        # - len(nrgs_lev_end) >= 2, meaning that multiple end level energies
        #   have been found for one start level energy.
        #
        if len(nrgs_lev_end) >= 2:
            # End level energy as start level energy
            if is_verbose:
                print('Multiple end energy levels:     {}'.format(
                    nrgs_lev_end))
            for ele_as_sle in nrgs_lev_end:
                if is_verbose:
                    print('Recursion with "ele_as_sle":    {}'.format(
                        ele_as_sle))
                nrgs_lev_end_tally += self.get_nrg_lev_end(
                    df_rn_gams,
                    ele_as_sle,
                    is_verbose=is_verbose)

        #
        # Recursive case (ii)
        # - len(nrgs_lev_end) == 1, meaning that at least one end level energy
        #   has been found; in other words, the start level energy in question
        #   has been found in the corresponding gamma dataset.
        #
        elif len(nrgs_lev_end) == 1:
            if True in bool_idx_sle.unique():
                if is_verbose:
                    print('Recursion with "nrgs_lev_end":  {}'.format(
                        nrgs_lev_end))
                nrgs_lev_end_tally += self.get_nrg_lev_end(
                    df_rn_gams,
                    nrgs_lev_end[0],
                    is_verbose=is_verbose)

        #
        # Tally the identified end level energies.
        #
        if is_verbose:
            print('Tallying "nrgs_lev_end":        {}'.format(
                nrgs_lev_end))
        nrgs_lev_end_tally += nrgs_lev_end

        #
        # Base case
        # - len(nrgs_lev_end) == 0, meaning that there is no end level energy;
        #   namely, there is no data row corresponding to the start level
        #   energy in question.
        #
        if is_verbose:
            msg = ('\nThe base case met!\n'
                   + 'Returning "nrgs_lev_end_tally": {}\n'.format(
                       nrgs_lev_end_tally))
            print(msg)
        return nrgs_lev_end_tally

    def set_gams(self, rn, nucl_data_path,
                 is_verbose=False):
        """Set the end level energies of gamma data of a radionuclide.

        Parameters
        ----------
        rn : str
            A radionuclide of interest whose end levels of gamma data will be
            retrieved and associated to its levs dictionary.
        nucl_data_path : str
            A directory containing nuclear data files.
        is_verbose : bool, optional
            If True, an error code and its meaning will be displayed when
            issued at get_livechart_df() via run_get_livechart_df().
            The default is False.

        Returns
        -------
        None.
        """
        # Generate a DF containing the gamma data of the radionuclide
        # in question.
        rn_lc = self.get_rn_alias(rn, how='plain2lc')
        decay_gams_fname_full = '{}/{}/{}_gammas.csv'.format(nucl_data_path,
                                                             rn,
                                                             rn)
        url_params_gams = {
            'fields': 'gammas',
            'nuclides': rn_lc,
        }
        df_rn_gams = self.run_get_livechart_df(
            decay_gams_fname_full,
            url_params_gams,
            nucl_data_nonexist_fname_full='',
            decay_radiat_type_pair='',
            is_verbose=is_verbose)
        # df will be "None" on data retrieval failure.
        if isinstance(df_rn_gams, pd.DataFrame):
            df_rn_gams['sle_llim'] = (df_rn_gams['start_level_energy']
                                      - df_rn_gams['unc_sle'])
            df_rn_gams['sle_ulim'] = (df_rn_gams['start_level_energy']
                                      + df_rn_gams['unc_sle'])
            nrg_lev_types = [k for k in self.levs[rn].keys()
                             if re.search('(?i)^from_', k)]
            if 'from_gamma_cascade' not in self.levs[rn]:
                self.levs[rn]['from_gamma_cascade'] = {}
            if 'energy_levels' not in self.levs[rn]['from_gamma_cascade']:
                self.levs[rn]['from_gamma_cascade']['energy_levels'] = []
            for nrg_lev_type in nrg_lev_types:  # e.g. from_Mo-99
                if nrg_lev_type == 'from_gamma_cascade':
                    continue
                for nrg_lev_p in self.levs[rn][nrg_lev_type]['energy_levels']:
                    # e.g. Th-234 --bm--> Pa-234m has <nrg>+X
                    nrg_lev_p = float(re.sub('(?i)[+]X', '', str(nrg_lev_p)))
                    if is_verbose:
                        msg = (f'Radionuclide: {rn},'
                               + f' nrg_lev_type: {nrg_lev_type},'
                               + f' nrg_lev_p: {nrg_lev_p}')
                        mt.show_warn(msg)
                    # Collect all feasible end level energies (eles)
                    # corresponding to each of the parent-inherited energy
                    # levels.
                    nrgs_lev_end = self.get_nrg_lev_end(df_rn_gams, nrg_lev_p,
                                                        is_verbose=is_verbose)
                    eles = [ele for ele in nrgs_lev_end
                            if ele not in self.levs[rn]['from_gamma_cascade'][
                                'energy_levels']]
                    # The list eles can contain duplicate energy levels,
                    # as one energy level can be associated with multiple
                    # transition paths.
                    # e.g. Tc-99 142.6836 keV
                    # - Transition 1: -> 0.0 keV (directly to the ground state)
                    # - Transition 2: -> 140.5110 keV -> 0.0 keV
                    # Without duplicate removal, eles would contain
                    # [0.0, 140.511, 0.0], which should be
                    # [0.0, 140.511].
                    # Although such duplicates will not be included in
                    # the practically important list energy_levels_flattened
                    # at set_levs_energy_flattening(), perform duplicate
                    # elimination here for cosmetic purposes, as the content
                    # of eles will appear in the level report file under
                    # from_gamma_cascade > energy_levels.
                    eles_uniq = list(dict.fromkeys(eles))
                    self.levs[rn]['from_gamma_cascade'][
                        'energy_levels'] += eles_uniq

    def set_levs(self, rn, nucl_data_path,
                 is_verbose=False):
        """Set the energy levels of decay modes of a radionuclide.

        Parameters
        ----------
        rn : str
            A radionuclide of interest whose levels will be retrieved
            and associated to its levs dictionary.
        nucl_data_path : str
            A directory containing nuclear data files.
        is_verbose : bool, optional
            If True, an error code and its meaning will be displayed when
            issued at get_livechart_df() via run_get_livechart_df().
            The default is False.

        Returns
        -------
        None.
        """
        # Generate a DF containing the level data of the radionuclide
        # in question.
        rn_lc = self.get_rn_alias(rn, how='plain2lc')
        decay_levs_fname_full = '{}/{}/{}_levels.csv'.format(nucl_data_path,
                                                             rn,
                                                             rn)
        url_params_levs = {
            'fields': 'levels',
            'nuclides': rn_lc,
        }
        df_rn_levs = self.run_get_livechart_df(
            decay_levs_fname_full,
            url_params_levs,
            nucl_data_nonexist_fname_full='',
            decay_radiat_type_pair='',
            is_verbose=is_verbose)
        # df will be "None" on data retrieval failure.
        if isinstance(df_rn_levs, pd.DataFrame):
            # Copy the DF for use at set_levs_feasibility().
            # Aliasing
            col_jp = self.cols['jp']['nucl_data_old']
            col_dm = self.cols['decay_mode']['nucl_data_old']
            #
            # Preprocessing for decay mode key modification
            #
            # Identify all the decay modes of the radionuclide associated with
            # its level. In general, only a limited number of levels are
            # directly linked to decay modes, and here we are narrowing down
            # the levels to those leading to decay modes.
            #
            # e.g. Tc-99
            # Ex (keV)   | Decay mode 1 and BR (%) | Decay mode 2 and BR (%)
            #    0.0     | B- 100                  | NaN
            #  140.5110  | NaN                     | NaN
            #  142.6836  | IT 99.9963              | B- 99.9963 0.0037
            #  181.09423 | NaN                     | NaN
            # (139 more) | NaN                     | NaN
            # 6000.6     | NaN                     | NaN
            #
            dms = []
            cols_dm = [f'decay_{i}' for i in list(range(1, 4))]
            for col_dm in cols_dm:  # decay_1, decay_2, decay_3
                # Collect decay modes appearing in the decay mode column
                # in question.
                bool_idx_dm = df_rn_levs[col_dm].notna()
                dms_colwise = df_rn_levs.loc[bool_idx_dm,
                                             col_dm].unique().tolist()
                dms += [dm for dm in dms_colwise if dm not in dms]
            #
            # Preprocessing for decay mode key modification
            # (i) A progenitor radionuclide whose name has been linked to
            # the levs dictionary at the preprocessing (1) above but not yet
            # been given a 'self' key
            # (ii) A daughter radionuclide whose name has been associated
            # with the levs dictionary at get_daughters() but not yet
            # been given a 'self' key before this function has been called;
            # only the key 'from_<parent>' is available at this point.
            #
            if 'self' not in self.levs[rn]:
                self.levs[rn]['self'] = {}
            #
            # Decay mode key modification
            #
            for dm in dms:  # e.g. A, B-, EC+B+, IT
                if dm not in self.levs[rn]['self']:
                    self.levs[rn]['self'][dm] = {}
                if ('is_energy_level_set' in self.levs[rn]['self'][dm]
                        and self.levs[rn]['self'][dm]['is_energy_level_set']):
                    continue
                # Deep-copy the radionuclide DF and select the indices of the
                # copy that contain the decay mode in question.
                df_rn_dm = df_rn_levs[df_rn_levs.eq(dm).any(axis=1)].copy()
                # Retrieve pairs of an angular momentum and parity
                # corresponding to the decay mode in question.
                self.levs[rn]['self'][dm]['jps'] = df_rn_dm[col_jp].to_list()
                # Retrieve pairs of an energy level and its uncertainty
                # corresponding to the decay mode in question.
                self.levs[rn]['self'][dm]['energy_levels'] = []
                nrg_lev_pairs = df_rn_dm[['energy', 'unc_e']].values.tolist()
                for nrg_lev_pair in nrg_lev_pairs:  # A list of lists
                    # Conditional for .nan (type: float): NaN to 0
                    if nrg_lev_pair[1] != nrg_lev_pair[1]:
                        nrg_lev_pair[1] = 0
                    nrg_lev_llim = nrg_lev_pair[0] - nrg_lev_pair[1]
                    nrg_lev_ulim = nrg_lev_pair[0] + nrg_lev_pair[1]
                    nrg_lev = [nrg_lev_llim, nrg_lev_ulim]
                    self.levs[rn]['self'][dm]['energy_levels'].append(
                        nrg_lev)
                # Mark that the energy levels of the decay mode in question
                # has been set.
                self.levs[rn]['self'][dm]['is_energy_level_set'] = True

    def set_levs_energy_flattening(self, rn,
                                   is_sort=True, is_sort_reverse=True):
        """Flatten all possible energy levels of a radionuclide.

        Parameters
        ----------
        rn : str
            A radionuclide whose possible energy levels will be flattened.
        is_sort : bool, optional
            If True, sort the flattened list of energies. The default is True.
        is_sort_reverse : bool, optional
            If True, sort the flattened list of energies in descending order.
            The default is True.

        Returns
        -------
        None.
        """
        #
        # Energy level flattening
        #
        # Types of energy levels
        # (i) from_<rn>: Lists of energy levels from the decay modes of
        # a parent radionuclide
        # (ii) from_user_input: A list of energy levels from the user
        # input file
        #
        # Use of flattened energy levels
        # (i) Decay mode feasibility judgement later in this function
        # (ii) Radionuclide-wise DF slicing at get_rnlib()
        #
        nrg_lev_types = [k for k in self.levs[rn].keys()
                         if re.search('(?i)^from_', k)]
        if 'energy_levels_flattened' not in self.levs[rn]:
            self.levs[rn]['energy_levels_flattened'] = []
        for nrg_lev_type in nrg_lev_types:  # e.g. from_Mo-99
            for nrg_lev_p in self.levs[rn][nrg_lev_type]['energy_levels']:
                # e.g. Th-234 --bm--> Pa-234m has <nrg>+X
                nrg_lev_p = float(re.sub('(?i)[+]X', '', str(nrg_lev_p)))
                if nrg_lev_p not in self.levs[rn]['energy_levels_flattened']:
                    self.levs[rn]['energy_levels_flattened'].append(nrg_lev_p)
        # Sort, if requested, the list of flattened energies.
        if is_sort:
            self.levs[rn]['energy_levels_flattened'] = sorted(
                self.levs[rn]['energy_levels_flattened'],
                reverse=is_sort_reverse)

    def set_levs_feasibility(self):
        """Set the feasibilities of the decay modes of a radionuclide series.

        Returns
        -------
        None.
        """
        for rn in self.levs.keys():
            # >> stable nuclide screening
            # A stable nuclide, positioned at the last of a radionuclide
            # chain, had not have a chance to have the 'self' key in other
            # functions so far if none of its energy levels has been linked to
            # a decay mode.
            # Examples include Tl-205 and Pb-208. There are many, however,
            # stable nuclides whose portions of levels are associated with
            # decay modes. This counter example includes O-18.
            if 'self' not in self.levs[rn]:
                self.levs[rn]['self'] = {}
            the_self = self.levs[rn]['self']  # Aliasing
            if len(the_self) == 0:
                continue
            # <<

            #
            # Energy level flattening
            # This preprocessing is required particularly for isomer
            # progenitors designated at the user input file, which could not
            # enter the get_daughters() function where
            # set_levs_energy_flattening() is called.
            #
            self.set_levs_energy_flattening(rn)

            #
            # Decay mode feasibility judgement
            #
            if 'energy_levels_isomer' not in self.levs[rn]:
                self.levs[rn]['energy_levels_isomer'] = []
            nrg_levs_isomer = self.levs[rn]['energy_levels_isomer']  # Aliasing
            for dm in the_self.keys():  # A, B-, EC+B+, IT, ...
                #
                # By default, all decay modes are considered False; only those
                # considered feasible after screening will be assigned True.
                #
                if 'is_feasible' not in the_self[dm]:
                    the_self[dm]['is_feasible'] = False
                if 'feasible_energies' not in the_self[dm]:
                    the_self[dm]['feasible_energies'] = []
                fsbl_nrgs = the_self[dm]['feasible_energies']  # Aliasing
                #
                # Examine each possible energy level if it falls under the
                # energy of the decay mode in question.
                # - If it does so, the decay mode in question is considered
                #   feasible.
                # - Additionally, mark if the decay mode in question is the
                #   result of the decay of a nuclear isomer.
                #   **This information will later be used for appending
                #   the "m" symbol to nuclear isomers at get_rnlib().**
                #
                for nrg_lev_p in self.levs[rn]['energy_levels_flattened']:
                    #
                    # Nuclear isomer types
                    #
                    # (i) Isomeric transition implies a nuclear isomer (but
                    # not vice versa).
                    # (ii) A nuclear isomer designated at the user input file
                    # The temporary key "energy_levels_isomer_progenitor"
                    # is required: If a nonisomeric radionuclide and its
                    # isomer are placed in the "parent" key in that order and,
                    # with the "is_isomer_progenitor" Boolean alone, the
                    # energy levels of the two progenitors, say 0 keV and
                    # 135.5 keV, respectively, will all be included in the
                    # "energy_levels_isomer" key, thereby making decay modes
                    # corresponding to the ground state a nuclear isomer.
                    #
                    is_isomer = bool(dm == 'IT')
                    for nrg_lev_d_dm in the_self[dm]['energy_levels']:
                        if nrg_lev_d_dm[0] <= nrg_lev_p <= nrg_lev_d_dm[1]:
                            the_self[dm]['is_feasible'] = True
                            # Nuclear isomer type (ii): See the explanation
                            # around "is_isomer = False" above for details.
                            if ('energy_levels_isomer_progenitor'
                                    in self.levs[rn]
                                    and nrg_lev_p in self.levs[rn][
                                        'energy_levels_isomer_progenitor']):
                                is_isomer = True
                            the_self[dm]['is_isomer'] = is_isomer
                            if (the_self[dm]['is_isomer']
                                    and nrg_lev_p not in nrg_levs_isomer):
                                nrg_levs_isomer.append(nrg_lev_p)
                            # Memorize the energy level that has been judged
                            # to be feasible. The purpose of this information
                            # archiving is to let the user know for what
                            # specific energy level(s), out of the many, the
                            # "is_feasible" Boolean has been judged.
                            if nrg_lev_p not in fsbl_nrgs:
                                fsbl_nrgs.append(nrg_lev_p)
            # Remove the temporary key used for screening a user-designated
            # isomer progenitor.
            if 'energy_levels_isomer_progenitor' in self.levs[rn]:
                del self.levs[rn]['energy_levels_isomer_progenitor']

    def get_rnlib(self, p):
        """Generate a radionuclide library by recursive computation.

        Parameters
        ----------
        p : dict
            A dictionary holding configurations for radionuclide library
            construction.

        Returns
        -------
        df_rnlib : pandas.core.frame.DataFrame
            A radionuclide library DF containing progenitors designated by
            user input and their progeny recursively computed, with their decay
            data coupled.
        """
        #
        # Preprocessing: Generate I/O directories in advance and a nonexistent
        # nuclear data registry file if not found.
        #
        io.mk_dir(p['io']['lib']['nucl_data_path'], is_yn=False)
        nonexist_dname = os.path.dirname(
            p['io']['lib']['nucl_data_nonexist_fname_full'])
        io.mk_dir(p['io']['out']['rpt_path'], is_yn=False)
        if p['io']['ctrls']['is_export']:
            io.mk_dir(p['io']['out']['export_path'], is_yn=False)
        io.mk_dir(nonexist_dname, is_yn=False)
        if not os.path.exists(p['io']['lib']['nucl_data_nonexist_fname_full']):
            open(p['io']['lib']['nucl_data_nonexist_fname_full'], 'w',
                 encoding='utf8').close()
            io.show_file_gen(p['io']['lib']['nucl_data_nonexist_fname_full'])

        #
        # Step 1. Construct a radionuclide subset by recursive computation,
        # and retrieve the corresponding nuclear data, if unavailable
        # in the local disk, from the user-designated nuclear database.
        #
        # Energy level feasibility validation (1/5): Individually specified
        # static isomers
        if len(p['scout']['radionuclides']['static']) >= 1:
            for i, progenitor_stat in enumerate(
                    p['scout']['radionuclides']['static']):
                if not progenitor_stat:  # Empty element
                    continue
                progenitor_stat = self.set_progenitor(progenitor_stat)
                p['scout']['radionuclides']['static'][i] = progenitor_stat
                self.set_gams(progenitor_stat,
                              p['io']['lib']['nucl_data_path'])
                self.set_levs(progenitor_stat,
                              p['io']['lib']['nucl_data_path'])
        # Identify the progeny of each user-designated recursive progenitor.
        if len(p['scout']['radionuclides']['recursive']) >= 1:
            # Assign an empty list in case none of the designated
            # recursive progenitors has progeny.
            decay_chains_flattened = []
            daughters = []
            for i, progenitor_recursive in enumerate(
                    p['scout']['radionuclides']['recursive']):
                if not progenitor_recursive:  # Empty element
                    continue
                # Energy level feasibility validation (2/5): An isomeric
                # recursive progenitor
                # - After making its isomer status Boolean true (note that
                #   isomeric progeny radionuclides are assigned their Boolean
                #   at set_levs_feasibility(); see validation (4/5) below),
                #   remove the trailing "m" symbol from the recursive
                #   progenitor name for:
                #   (i) compatibility with the nuclear data file name and
                #       hence for correct parsing at get_daughters()
                #       (modify the temporary delegate variable
                #       "progenitor_recursive")
                #   (ii) correct construction of _rn_subset (modify the
                #        actual element of ['radionuclides']['recursive'])
                progenitor_recursive = self.set_progenitor(
                    progenitor_recursive)
                p['scout']['radionuclides']['recursive'][
                    i] = progenitor_recursive
                # Energy level feasibility validation (3/5): The gamma
                # cascades and energy levels of a recursive progenitor
                self.set_gams(progenitor_recursive,
                              p['io']['lib']['nucl_data_path'])
                self.set_levs(progenitor_recursive,
                              p['io']['lib']['nucl_data_path'])
                # **Create a list of all possible progeny nuclides.**
                daughters = self.get_daughters(
                    progenitor_recursive,
                    p['io']['lib']['nucl_data_path'],
                    p['io']['lib']['nucl_data_nonexist_fname_full'],
                    is_verbose=p['io']['ctrls']['is_verbose'])
                # Save the constructed decay chain of the recursive progenitor
                # to a report file.
                p['io']['out']['lineage_fname'] = '{}_{}{}.yaml'.format(
                    p['io']['out']['lineage_bname'],
                    progenitor_recursive,
                    '_lineage')
                p['io']['out']['lineage_fname_full'] = '{}/{}'.format(
                    p['io']['out']['rpt_path'],
                    p['io']['out']['lineage_fname'])
                io.dump_yaml(
                    self.lineage,
                    msg=f'# Identified lineage of {progenitor_recursive}\n\n',
                    is_savetxt=True,
                    txt_fname_full=p['io']['out']['lineage_fname_full'])
                self.lineage = {}  # Initialize for the next progenitor.
                # Remove duplicates, if any, from the identified daughters
                # of the recursive progenitor in question.
                daughters_uniq = list(dict.fromkeys(daughters))
                # Construct a decay chain of the progenitor and its progeny.
                decay_chains_flattened.append(progenitor_recursive)
                decay_chains_flattened += daughters_uniq
        # Energy level feasibility validation (4/5): Daughter radionuclides
        self.set_levs_feasibility()
        # Save the energy levels of the radionuclides to a report file.
        p['io']['out']['lev_fname_full'] = '{}/{}{}.yaml'.format(
            p['io']['out']['rpt_path'],
            p['io']['out']['lev_bname'],
            '_levels')
        io.dump_yaml(
            self.levs,
            msg='# Energy levels of the involved radionuclides\n\n',
            is_savetxt=True,
            txt_fname_full=p['io']['out']['lev_fname_full'])

        # Remove empty strings, if any, from the list of static radionuclides.
        # An empty string corresponds to an entry of "" under
        # scout > radionuclides > static in the user input file.
        _static_rns = [d for d in p['scout']['radionuclides']['static'] if d]
        p['scout']['radionuclides']['static'] = _static_rns

        # - Create a complete radionuclide subset by combining the flattened
        #   decay chains and static radionuclides.
        # - Remove duplicates, if any, from the radionuclide subset.
        _rn_subset = (decay_chains_flattened
                      + p['scout']['radionuclides']['static'])
        self.rn_subset_uniq = list(dict.fromkeys(_rn_subset))

        # - Remove the user-specified exclusion group, if any.
        if ('exclusion' in p['scout']['radionuclides']
                and len(p['scout']['radionuclides']['exclusion'])):
            for excl in p['scout']['radionuclides']['exclusion']:
                if excl in self.rn_subset_uniq:
                    self.rn_subset_uniq.remove(excl)
        # <<

        #
        # Step 2. Generate a radionuclide-wise library DF.
        #
        # >> Aliasing
        _usecols = [
            'energy',
            'energy_unc',
            'emission_probability',
            'emission_probability_unc',
            'energy_level',
            'jp',
            'half_life',
            'half_life_unc',
            'half_life_unit',
            'half_life_sec',
            'decay_mode',
            'decay_branching_fraction',
            'decay_branching_fraction_unc',
            'database_literature_cutoff_date',
            'database_literature_authors',
            'database_access_date',
        ]
        usecols = [self.cols[col]['nucl_data_old'] for col in _usecols]
        col_rn = self.cols['radionuclide']['nucl_data_new']
        col_radiat_num = self.cols['radiation_number']['nucl_data_new']
        col_key_radiat_bool = self.cols['key_radiation_bool']['nucl_data_new']
        col_nrg = self.cols['energy']['nucl_data_old']
        col_ep = self.cols['emission_probability']['nucl_data_old']
        col_nrg_lev = self.cols['energy_level']['nucl_data_old']
        col_hl_sec = self.cols['half_life_sec']['nucl_data_old']
        col_dm = self.cols['decay_mode']['nucl_data_old']
        col_db = self.cols['database']['nucl_data_new']
        nrg_lim = [float(nrg) for nrg
                   in p['scout']['radionuclides']['cutoffs']['energy']]
        ep_lim = [float(ep) for ep
                  in p['scout']['radionuclides']['cutoffs']
                      ['emission_probability']]
        hl_sec_lim = [float(hl) for hl
                      in p['scout']['radionuclides']['cutoffs'][
                          'half_life_sec']]
        # <<
        dfs_rnlib_to_be_concated = []
        for rn in self.rn_subset_uniq:
            # A possible "m" symbol denoting a nuclear isomer had certainly
            # been dropped at this point, but to avoid any potential errors
            # related to the Live Chart of Nuclides notation, use a regex sub
            # as below.
            rn_wo_possible_m = re.sub('(?i)m$', '', rn)
            decay_radiat_type_pair = '{}_{}'.format(rn_wo_possible_m,
                                                    self.radiat['short'])
            decay_fname_full = '{}/{}/{}.csv'.format(
                p['io']['lib']['nucl_data_path'],
                rn_wo_possible_m,
                decay_radiat_type_pair)
            # Skip the current radionuclide if there is no corresponding
            # nuclear data file in the user-specified directory.
            # This applies to stable daughter nuclides, which obviously
            # have no nuclear data files but are still included in
            # the self.rn_subset_uniq list as they form the base
            # cases of the recursion of get_daughters().
            if not os.path.exists(decay_fname_full):
                continue
            # A radionuclide-wise library DF containing a single radionuclide
            # and its nuclear data
            df_rnlib_rnwise = pd.read_csv(decay_fname_full,
                                          usecols=usecols)
            # Slice the DF with respect to the user-specified energy and
            # emission probability cutoff values.
            # e.g. Bi-215_g.csv, index 0, energy: X (str)
            df_rnlib_rnwise[col_nrg] = pd.to_numeric(
                df_rnlib_rnwise[col_nrg], errors='coerce')
            bool_idx_cuton = ((df_rnlib_rnwise[col_nrg] >= nrg_lim[0])
                              & (df_rnlib_rnwise[col_nrg] <= nrg_lim[1])
                              & (df_rnlib_rnwise[col_ep] >= ep_lim[0])
                              & (df_rnlib_rnwise[col_ep] <= ep_lim[1])
                              & (df_rnlib_rnwise[col_hl_sec] >= hl_sec_lim[0])
                              & (df_rnlib_rnwise[col_hl_sec] <= hl_sec_lim[1]))
            df_rnlib_rnwise = df_rnlib_rnwise[bool_idx_cuton]
            # Skip the current radionuclide if the sliced DF does not have
            # nuclear data (cases where all data rows have been pruned).
            if not len(df_rnlib_rnwise.index):
                continue
            # Prepend columns to the radionuclide-wise radionuclide library DF
            # containing:
            #   1. Radionuclide name
            #   2. Radiation number
            #   3. Key radiation Boolean
            # - Note that they are inserted to the 0th column in reverse order.
            # - The radionuclide name must be inserted before energy level
            #   validation step 5, where nuclear isomers are assigned the "m"
            #   suffix on top of their nuclide names.
            ep_max = df_rnlib_rnwise[col_ep].max()
            bool_idx_ep_max = df_rnlib_rnwise[col_ep] == ep_max
            df_rnlib_rnwise.insert(0, col_key_radiat_bool,
                                   bool_idx_ep_max.astype(int))
            df_rnlib_rnwise.insert(0, col_radiat_num,
                                   range(1, len(df_rnlib_rnwise.index) + 1))
            df_rnlib_rnwise.insert(0, col_rn,
                                   [rn] * len(df_rnlib_rnwise.index))
            # Energy level feasibility validation (5/5)
            # 1. Select only feasible nuclear data rows by
            #   - slicing the DF based on the possible list of energy levels
            #   - removing unfeasible decay modes
            # 2. Append the "m" symbol to nuclear isomers in the radionuclide-
            #    wise DF based on the levs dictionary.
            if rn in self.levs:
                #
                # Remove physically unviable energy levels from the DF.
                #
                if p['io']['ctrls']['is_verbose']:
                    print(f'\nRadionuclide: [{rn}], possible'
                          + ' energy levels:'
                          + ' {}\n'.format(
                              self.levs[rn]['energy_levels_flattened'])
                          + 'Before:')
                    print(df_rnlib_rnwise.iloc[:, list(range(4)) + [-1]])
                bool_idx_nrg_lev_incl = df_rnlib_rnwise[col_nrg_lev].isin(
                    self.levs[rn]['energy_levels_flattened'])
                df_rnlib_rnwise = df_rnlib_rnwise[bool_idx_nrg_lev_incl]
                if p['io']['ctrls']['is_verbose']:
                    print('\nAfter:')
                    print(df_rnlib_rnwise.iloc[:, list(range(4)) + [-1]])
                #
                # Remove physically unviable decay modes from the DF.
                #
                for dm in self.levs[rn]['self'].keys():
                    bool_idx_dm = df_rnlib_rnwise[col_dm] == dm
                    if not self.levs[rn]['self'][dm]['is_feasible']:
                        if p['io']['ctrls']['is_verbose']:
                            print(f'\nRadionuclide: [{rn}],'
                                  + f' unfeasible decay mode: [{dm}]\n'
                                  + 'Before:')
                            print(df_rnlib_rnwise)
                        df_rnlib_rnwise.drop(
                            df_rnlib_rnwise[bool_idx_dm].index,
                            axis=0,
                            inplace=True)
                        if p['io']['ctrls']['is_verbose']:
                            print('\nAfter:')
                            print(df_rnlib_rnwise)
                #
                # Nuclear isomer labeling (appending "m" to the mass number)
                #
                if p['io']['ctrls']['is_verbose']:
                    print(f'\nRadionuclide: [{rn}], nuclear'
                          + ' isomer energy levels:'
                          + ' {}\n'.format(
                              self.levs[rn]['energy_levels_isomer'])
                          + 'Before:')
                    print(df_rnlib_rnwise)
                bool_idx_nrg_lev_isomer = df_rnlib_rnwise[col_nrg_lev].isin(
                    self.levs[rn]['energy_levels_isomer'])
                the_rns = df_rnlib_rnwise.loc[bool_idx_nrg_lev_isomer,
                                              col_rn].replace('([0-9])$',
                                                              r'\1m',
                                                              regex=True)
                df_rnlib_rnwise.loc[bool_idx_nrg_lev_isomer, col_rn] = the_rns
                if p['io']['ctrls']['is_verbose']:
                    print('\nAfter:')
                    print(df_rnlib_rnwise)
            #
            # Differentiation of a radionuclide and its isomer
            # - Sort the DF, which had been created with respect to the nuclear
            #   data order of the Live Chart of Nuclides with the isomers
            #   undifferentiated, by the radionuclide and its isomer.
            # - Reassign the following attributes separately to the
            #   radionuclide and its isomer:
            #   - Radiation peak numbers
            #   - Key radiation Boolean
            #
            rn_w_forced_m = re.sub('([0-9])$', r'\1m', rn)
            if df_rnlib_rnwise[col_rn].isin([rn_w_forced_m]).any():
                if p['io']['ctrls']['is_verbose']:
                    print(f'\nRadionuclide: [{rn}], nuclear'
                          + ' isomer: [{rn_w_forced_m}]'
                          + 'Before reorganization:')
                    print(df_rnlib_rnwise)
                # Sort the DF such that the nuclear isomer comes first
                # while maintaining the order of radiation data points
                # originated from the Live Chart of Nuclides.
                # e.g. Before:
                # Radionuclide | Radiation number | Radiation energy (keV)
                # Tc-99        | 1                | 89.5
                # Tc-99m       | 2                | 89.6
                # Tc-99m       | 3                | 140.511
                # ...
                # After:
                # Radionuclide | Radiation number | Radiation energy (keV)
                # Tc-99m       | 2                | 89.6
                # Tc-99m       | 3                | 140.511
                # ...
                # Tc-99        | 1                | 89.5
                # ...
                df_rnlib_rnwise.sort_values(by=[col_rn, col_radiat_num],
                                            ascending=[False, True],
                                            ignore_index=True,
                                            inplace=True)
                bool_idx_isomer = df_rnlib_rnwise[col_rn] == rn_w_forced_m
                bool_idx_rn = df_rnlib_rnwise[col_rn] == rn
                # Attribute reassignment (i): Radiation numbers
                radiat_num_isomer = range(
                    1,
                    len(df_rnlib_rnwise.loc[bool_idx_isomer].index) + 1)
                radiat_num_rn = range(
                    1,
                    len(df_rnlib_rnwise.loc[bool_idx_rn].index) + 1)
                df_rnlib_rnwise.loc[bool_idx_isomer,
                                    col_radiat_num] = radiat_num_isomer
                df_rnlib_rnwise.loc[bool_idx_rn,
                                    col_radiat_num] = radiat_num_rn
                # Attribute reassignment (ii): Key radiation Booleans
                ep_max_isomer = df_rnlib_rnwise.loc[bool_idx_isomer,
                                                    col_ep].max()
                ep_max_rn = df_rnlib_rnwise.loc[bool_idx_rn,
                                                col_ep].max()
                bool_idx_ep_max_isomer = df_rnlib_rnwise.loc[
                    bool_idx_isomer,
                    col_ep] == ep_max_isomer
                bool_idx_ep_max_rn = df_rnlib_rnwise.loc[
                    bool_idx_rn,
                    col_ep] == ep_max_rn
                df_rnlib_rnwise.loc[
                    bool_idx_isomer,
                    col_key_radiat_bool] = bool_idx_ep_max_isomer.astype(int)
                df_rnlib_rnwise.loc[
                    bool_idx_rn,
                    col_key_radiat_bool] = bool_idx_ep_max_rn.astype(int)
                if p['io']['ctrls']['is_verbose']:
                    print('\nAfter:')
                    print(df_rnlib_rnwise)
            # Append a column containing the name of the nuclear database
            # in question to the radionuclide-wise DF.
            df_rnlib_rnwise[col_db] = p['io']['lib']['nucl_database']
            # Add the radionuclide-wise DF to a list which will in turn be
            # combined into one DF.
            dfs_rnlib_to_be_concated.append(df_rnlib_rnwise)

        # Combine the radionuclide-wise radionuclide library DFs into one DF,
        # which will yield a single, comprehensive radionuclide library DF.
        df_rnlib = pd.concat(dfs_rnlib_to_be_concated)
        # Rename the column names using the user-specified column names.
        df_rnlib.rename(columns=self.cols['nucl_data_to_rpt'],
                        inplace=True)
        # Sort the combined DF by the values of the user-specified column.
        if p['io']['cols_sort']['toggle']:
            sort_by = p['io']['cols_sort']['by']  # e.g. 'energy'
            if re.search('(?i)radionuclide', sort_by):
                # Force the legend order to be 'as_is'.
                p['plot']['annots']['grouped']['legend']['order'] = 'as_is'
                # Sort the DF using custom keys.
                sort_dct = {k: i for i, k in enumerate(self.rn_subset_uniq)}
                df_rnlib.sort_values(by=self.cols[sort_by]['nucl_data_new'],
                                     key=lambda col: col.map(sort_dct),
                                     inplace=True)
            else:
                df_rnlib.sort_values(by=self.cols[sort_by]['nucl_data_new'],
                                     inplace=True)
        # Reset the index of the radionuclide library DF.
        df_rnlib.reset_index(drop=True, inplace=True)
        df_rnlib.index.name = 'Library index'
        return df_rnlib

    def get_context(self, rnlib_bname, df_rnlib,
                    df_col_type='nucl_data_new', is_verbose=False):
        """Construct a context dict for Jinja rendering.

        Parameters
        ----------
        rnlib_bname : str
            The base name of a radionuclide library.
        df_rnlib : pandas.core.frame.DataFrame
            A radionuclide library DF containing progenitors designated by
            user input and their progeny recursively computed, with their decay
            data coupled.
        df_col_type : str, optional
            The DF column name type. The default is 'nucl_data_new'.
            This must corresponds to that used in df_rnlib passed here
            together.
        is_verbose : bool, optional
            If True, the constructed context will be displayed. The default
            is False.

        Returns
        -------
        context : dict
            A context dictionary constructed for Jinja rendering.
        """
        #
        # Preprocessing
        #
        df_context = df_rnlib.copy()  # Do not alter the original DF.
        df_context.fillna(0, inplace=True)  # .nan -> 0

        #
        # Radionuclide library information
        #
        prog_name = 'RecurLib'
        col_db = self.cols['database'][df_col_type]
        nucl_database = df_context[col_db].to_list()[0]
        now = time.localtime()
        now_ymd = time.strftime('%B %d, %Y', now)
        now_hms = time.strftime('%H:%M:%S', now)
        now_utc = re.sub('([0-9]{2})([0-9]{2})', r'\1:\2',
                         time.strftime('%z', now))
        tstamp = 'Generated on {}, at {} (UTC {})'.format(now_ymd,
                                                          now_hms,
                                                          now_utc)
        # Restrict the library code length to 32 characters to ensure
        # compatibility with some third-party spectral analysis software.
        rnlib_code_bname = '{}-{}'.format(prog_name.lower(), rnlib_bname)
        rnlib_code_bname = rnlib_code_bname[:28]
        rnlib_info = {
            'code_master': '{}-mst'.format(rnlib_code_bname),
            'code_group': '{}-grp'.format(rnlib_code_bname),
            'name': '{}-{} ({} v{}; {})'.format(prog_name.lower(),
                                                rnlib_bname,
                                                prog_name,
                                                __version__,
                                                nucl_database),
            'comment': tstamp,
        }

        #
        # Radionuclide information
        #
        # Extract radionuclide information and its decay radiation
        # separately for each radionuclide contained in the radionuclide
        # library.
        #
        cols_rn_info = [
            'radionuclide',
            'half_life',
            'half_life_unc',
            'half_life_unit',
            'half_life_sec',
        ]
        cols_radiat = [
            'radiation_number',
            'energy',
            'energy_unc',
            'emission_probability',
            'emission_probability_unc',
            'key_radiation_bool',
        ]
        # Iterate over the list of radionuclides contained in the library DF.
        col_rn = self.cols['radionuclide'][df_col_type]
        rns = {rn: {'radiats': []} for rn in df_context[col_rn].unique()}
        rns_gr_from_isomer = {rn: False for rn in rns}
        for rn in rns:
            # Associate the name and half-life data of a radionuclide
            # to context dict.
            bool_idx_rn = df_context[col_rn] == rn
            for col in cols_rn_info:
                # col: A column key in the user input
                # col_in_df: A Column name in the DF
                col_in_df = self.cols[col][df_col_type]
                # e.g. ['Ac-225', 'Ac-225', ..., 'Ac-225'] -> 'Ac-225'
                rns[rn][col] = df_context.loc[bool_idx_rn,
                                              col_in_df].to_list()[0]
            # Create an identification code of the radionuclide in question
            # and extract its element symbol and mass number.
            rn_code = self.get_rn_alias(rns[rn]['radionuclide'],
                                        how='plain2code')
            elem_symb, mass_num = rns[rn]['radionuclide'].split('-')
            mass_num_wo_possible_m = re.sub('(?i)m$', '', mass_num)
            rns[rn]['code'] = rn_code
            rns[rn]['element_symbol'] = elem_symb
            rns[rn]['mass_number'] = mass_num_wo_possible_m
            # Retrieve the parent and daughter information from the levs dict.
            # e.g. parents = ['Ac-225'], daughters = ['At-217']
            # -> {'parent': 'Ac-225', 'parent_code': 'AC225'}
            # -> {'daughter': 'At-217', 'daughter_code': 'AT217'}
            rn_wo_possible_m = re.sub('(?i)m$', '', rn)
            for ps_or_ds in ['parents', 'daughters']:
                # - Skip defining the parent attribute if the radionuclide is
                #   the ground state achieved by the de-excitation of its
                #   isomeric state.
                # - Example: rns = ['Mo-99', 'Tc-99m', 'Tc-99']
                #   At rn == 'Tc-99', without the conditional below, its
                #   parent attribute, which had been defined in the preceding
                #   radionuclide 'Tc-99m' at "Attribute overwriting at
                #   a nuclear isomer" in the next block, will be reassessed
                #   and overwritten by 'Mo-99'.
                # - However, the daughter attribute of the ground state
                #   must still be defined in this block.
                if (ps_or_ds == 'parents'
                        and rns_gr_from_isomer[rn]):
                    continue
                p_or_s = ps_or_ds.rstrip('s')
                if ps_or_ds in self.levs[rn_wo_possible_m]:
                    p_or_s_name = self.levs[rn_wo_possible_m][ps_or_ds][-1]
                    p_or_s_code = self.get_rn_alias(p_or_s_name,
                                                    how='plain2code')
                    rns[rn][p_or_s] = p_or_s_name
                    rns[rn][f'{p_or_s}_code'] = p_or_s_code
            #
            # Attribute overwriting at a nuclear isomer
            #
            # When the current radionuclide is a nuclear isomer, do:
            # - redefine its daughter attribute, which had been defined to be
            #   the daughter of the ground state of the isomer as the levs
            #   dictionary does not differentiate a radionuclide and its
            #   isomer.
            #   e.g. Tc-99m --daughter-- Ru-99
            #        -> Tc-99m --daughter-- Tc-99
            # - define in advance the parent attribute of the ground-state
            #   radionuclide.
            #   e.g. <rn> --parent-- Tc-99
            #        -> Tc-99m --parent-- Tc-99
            if re.search('(?i)m$', rn):
                for _lev in self.levs[rn_wo_possible_m]['from_gamma_cascade'][
                        'energy_levels']:
                    # - The conditional below means that over the course of
                    #   de-excitation of the nuclide isomer, its ground state
                    #   is achieved. Note that there are nuclear isomers that
                    #   do not undergo isomeric transition and, therefore,
                    #   having a nuclear isomer does not necessarily mean
                    #   that there will always be its ground state.
                    # - For example, Nb-92m, which can be produced by the
                    #   photonuclear reaction Mo-94(g,np), decays only by
                    #   either electron capture or beta plus decay.
                    #   Therefore, to establish an isomer-ground state relation
                    #   from the perspective of an isomer, we have to ensure
                    #   that there is 0 keV involved in the electromangetic
                    #   transitions of the isomer in question.
                    if _lev == 0:
                        # The daughter attribute of an isomeric
                        d_name = rn_wo_possible_m
                        d_code = self.get_rn_alias(d_name,
                                                   how='plain2code')
                        rns[rn]['daughter'] = d_name
                        rns[rn]['daughter_code'] = d_code
                        # The parent attribute of the ground state
                        p_name = rn
                        p_code = self.get_rn_alias(p_name,
                                                   how='plain2code')
                        # Skip if the ground state is a stable nuclide,
                        # in which case the nuclide is not included
                        # in the radionuclide library. Anyways,
                        # the rns dict does not have the nuclide in its
                        # keys after all.
                        # e.g. The ground state of Y-89m (Y-89m is a daughter
                        # radionuclide of Zr-89), or Y-89, is stable.
                        if d_name in rns:
                            rns[d_name]['parent'] = p_name
                            rns[d_name]['parent_code'] = p_code
                            rns_gr_from_isomer[d_name] = True
            # Radionuclide-wise indices of the library DF converted to dicts
            rnwise_dicted = df_context.loc[bool_idx_rn].to_dict(orient='index')
            for rn_dct in rnwise_dicted.values():
                # An anonymous dict to be appended to the 'radiats' list
                anonymous_dct = {}
                for col in cols_radiat:
                    # e.g. Example dicts to be added to the 'radiats' list:
                    # {'radiation_number': 1, 'energy': 26.0, ...,
                    #  'key_radiation_bool': 0}
                    # {'radiation_number': 2, 'energy': 36.7, ...,
                    #  'key_radiation_bool': 0}
                    col_in_df = self.cols[col][df_col_type]
                    anonymous_dct.update({col: rn_dct[col_in_df]})
                rns[rn]['radiats'].append(anonymous_dct)

        #
        # Construct and return a Jinja context dict.
        #
        context = {
            'rnlib_info': rnlib_info,
            'rns': rns,
        }
        if is_verbose:
            print()
            mt.show_warn('Jinja context')
            io.dump_yaml(context)
        return context

    def run_recurlib(self, the_ini, the_yml):
        """Run recursive generation of a radionuclide library.

        Parameters
        ----------
        the_ini : dict
            A dictionary containing initialization configurations.
        the_yml : dict
            A dictionary containing library generation configurations.

        Returns
        -------
        None.
        """
        #
        # Iterate over the active datasets designated in the user input file.
        #
        if the_yml['active_datasets'] is None:  # Empty list
            msg = ('[active_datasets] has no element.'
                   + ' Terminating the program.')
            mt.show_warn(msg)
            sys.exit()
        for adataset in the_yml['active_datasets']:
            # >> Dataset name validation
            is_skip = False
            if not adataset:
                msg = (f'Warning: A null element name [{adataset}];'
                       + ' skipping.')
                is_skip = True
            if adataset not in the_yml:  # Wrong key
                msg = (f'Warning: [{adataset}] not in [{argv.file}];'
                       + ' skipping.')
                is_skip = True
            if re.search('(?i)active_datasets', adataset):
                msg = ('Warning: [active_datasets] is not allowed as an'
                       + ' element name under [active_datasets];'
                       + ' skipiing.')
                is_skip = True
            if is_skip:
                mt.show_warn(msg)
                continue
            # <<

            # Notification
            mt.show_msg(f'Working on [{adataset}]...')

            #
            # Construct the configuration dict of an active dataset.
            # (1) Copy all the key-val pairs of all nested dictionaries of
            # the 'template' key to an active dataset.
            # (2) Override the key-val pairs designated at the active dataset
            # at the active dataset dict.
            #
            inherited = copy.deepcopy(the_ini['template'])
            the_yml[adataset] = mt.merge(inherited, the_yml[adataset])

            # Aliasing
            a = the_yml[adataset]

            # Initialize for the next active dataset.
            self.levs = {}

            #
            # Construct full-path file names.
            #
            # (1) Expand environment variables, if any, in the names of
            # user-specified files and directories.
            io_types = {
                'lib': ['nucl_data_path', 'nucl_data_nonexist_fname_full',
                        'marker_registry_fname_full'],
                'out': ['rpt_path', 'export_path', 'fig_path', 'flag'],
            }
            for io_type, fname_types in io_types.items():
                for fname_type in fname_types:
                    # Iterate over and expand environment variables, if any.
                    a['io'][io_type][fname_type] = os.path.expandvars(
                        a['io'][io_type][fname_type])

            # (2) Construct the base names of output files.
            out_bnames_of_int = [
                'lineage_bname',
                'lev_bname',
                'echo_bname',
                'rpt_bname',
                'fig_bname',
            ]
            out_bnames_of_int_prefixed = [
                'export_bname',
            ]
            out_bname = adataset + a['io']['out']['flag']
            out_bname_prefixed = 'recurlib_{}'.format(out_bname)
            for out_bname_of_int in out_bnames_of_int:
                a['io']['out'][out_bname_of_int] = out_bname
            for out_bname_of_int_prefixed in out_bnames_of_int_prefixed:
                a['io']['out'][out_bname_of_int_prefixed] = out_bname_prefixed

            #
            # Construct a radionuclide library DF holding user-designated
            # progenitors and their identified progeny radionuclides with
            # their nuclear data coupled.
            #
            self.set_radiat(a['scout']['radionuclides']['spectrum_radiation'])
            self.set_cols(a['io']['cols'])
            self.df_rnlib = self.get_rnlib(a)

            #
            # Save the YAML content of the active dataset to a report file.
            #
            if a['io']['ctrls']['is_echo']:
                a['io']['out']['echo_fname_full'] = '{}/{}_echo.yaml'.format(
                    a['io']['out']['rpt_path'],
                    a['io']['out']['echo_bname'])
                io.dump_yaml(
                    a,
                    msg=f'# Echoed content of {adataset}\n\n',
                    is_savetxt=True,
                    txt_fname_full=a['io']['out']['echo_fname_full'])

            #
            # Save the radionuclide library DF to report files.
            #
            if a['io']['ctrls']['is_rpt']:
                xl_sheet_name = '{}_library'.format(self.radiat['long'])
                # XML-only DF
                self.df_rnlib_xml = self.df_rnlib.rename(
                    columns=self.cols['rpt_to_xml']).copy()
                # The strings contained in the values of rpt_to_xml dict
                # are the ones specified in the user input file.
                # Below the XML-only DF is reduced to these columns because
                # they are mean to be those required in the .xml-mediated
                # import/export in third-party spectral analysis software;
                # not all columns of the original radionuclide library DF
                # are used in import/export process.
                cols_xml = self.cols['rpt_to_xml'].values()
                self.df_rnlib_xml = self.df_rnlib_xml.loc[:, cols_xml]
                for fmt in a['io']['ctrls']['rpt_fmts']:
                    fmt = fmt.lower()
                    _df = self.df_rnlib if fmt != 'xml' else self.df_rnlib_xml
                    io.save_df(_df,
                               a['io']['out']['rpt_path'],
                               a['io']['out']['rpt_bname'],
                               fmt=fmt,
                               xl_sheet_name=xl_sheet_name)

            #
            # Generate a cross-platform radionuclide library file (.xml).
            #
            if (a['io']['ctrls']['is_export']
                    and len(a['io']['lib']['export_templates'])):
                context = self.get_context(
                    adataset, self.df_rnlib,
                    is_verbose=a['io']['ctrls']['is_verbose'])
                for tpl in a['io']['lib']['export_templates']:
                    io.save_jinja(context,
                                  tpl,
                                  a['io']['out']['export_path'],
                                  a['io']['out']['export_bname'])

            #
            # Plot the decay radiation of each radionuclide in the generated
            # radionuclide library.
            #
            # Note that the set_plot_style() method of a Painter object
            # must be called before the instantiation of an MPL Figure object;
            # otherwise the MPL style and rcParams will not be applied to
            # the first active dataset of this iteration.
            #
            creator = painter.Painter()
            creator.set_plot_style(a['plot'])
            fig, ax = plt.subplots(figsize=a['plot']['ax']['figsize'])
            creator.plot_radiat_spectr(fig, ax, a, self.df_rnlib, self.cols,
                                       x='energy', y='emission_probability',
                                       plot_type='rn')


if __name__ == '__main__':
    from modules import mytoolkit as mt
    from modules import inpout
    from modules import painter

    # Run time measurement - Beginning
    time_ref = time.monotonic()

    #
    # Front matter
    #
    prog_name = 'RecurLib'
    prog_info = {
        'name': prog_name,
        'desc': 'A recursion-based radionuclide library generator',
        'vers': __version__,
        'date': __date__,
        'auth': {
            'name': __author__,
            'affi': 'Isotope Science Center, University of Tokyo',
            'mail': 'jang[at]ric.u-tokyo.ac.jp',
        },
    }
    mt.show_front_matter(prog_info)

    #
    # I/O
    #
    io = inpout.InpOut()
    argv = io.read_argv(desc=prog_info['desc'],
                        ini_dflt='./inp/ini_recurlib.yaml')
    the_ini = io.read_yaml(argv.ini,
                           is_echo=argv.is_echo)
    the_yml = io.read_yaml(argv.file,
                           is_echo=argv.is_echo)

    # Construct a radionuclide library.
    recurlib = Recurlib()
    recurlib.run_recurlib(the_ini, the_yml)

    # Run time measurement - End
    time_elapsed = time.monotonic() - time_ref
    print('Elapsed real time: [{:.1f} s]'.format(time_elapsed))


elif __name__ == 'modules.recurlib':
    from modules import mytoolkit as mt
    from modules import inpout
    io = inpout.InpOut()
