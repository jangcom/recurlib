#!/usr/bin/env python3
"""mytoolkit: A suite of frequently used custom functions

This module houses functions written and used frequently by
the author in his Python programs.

Functions
---------
get_borders(border_len=70)
    Create a list of display borders.
get_now(ymd_directive='%B %d, %Y', hms_directive='%H:%M:%S',
        ymd_preposition='', hms_preposition='',
        is_ymd_wo_leading_zeros=True, is_append_utc=True)
    Return the current time in a formatted string.
get_target_sum(tgt_sum, objs, r, unc=0)
    Find a target sum from a pool of candidates using brute-force search.
merge(destination, source)
    Deeply merge two dictionaries.
pause_shell(second)
    Pause the shell during the designated time expressed in second.
invoke_yn_prompt(msg='Run (y/n)? ')
    Invoke a y/n selection prompt.
centering(s, ref_len=70)
    Center a string with respect to a user-specified string length.
show_msg(msg, border_symb='-', is_bordered=False, is_centered=False)
    Display a message with an optional pair of display borders.
show_warn(msg)
    Display a warning message with a pair of display borders.
show_front_matter(prog_info, is_prog=True, is_auth=True)
    Display a program front matter.
"""

import sys
import re
import time
from itertools import combinations

__author__ = 'Jaewoong Jang'
__copyright__ = 'Copyright (c) 2024 Jaewoong Jang'
__license__ = 'MIT License'
__version__ = '1.0.0'
__date__ = '2024-05-05'

BORDERS = {}


def get_borders(border_len=70):
    """Create a list of display borders.

    Parameters
    ----------
    border_len : int, optional
        The length of display borders. The default is 70.

    Returns
    -------
    None.
    """
    border_symbs = ['+', '-', '*', '#']
    for symb in border_symbs:
        BORDERS[symb] = symb * border_len
        BORDERS['{symb}-'] = symb + '-' * (border_len - 1)


def get_now(ymd_directive='%B %d, %Y', hms_directive='%H:%M:%S',
            ymd_preposition='', hms_preposition='',
            is_ymd_wo_leading_zeros=True, is_append_utc=True):
    """Return the current time in a formatted string.

    Parameters
    ----------
    ymd_directive : str, optional
        A year-month-day directive. The default is '%B %d, %Y'.
    hms_directive : str, optional
        An hour-minute-second directive. The default is '%H:%M:%S'.
    ymd_preposition : str, optional
        A preposition for date. You may use 'on '. The default is ''.
    hms_preposition : str, optional
        A preposition for time. You may use 'at '. The default is ''.
    is_ymd_wo_leading_zeros : bool, optional
        Remove leading zeros, if any, from month and day. The default is True.
    is_append_utc : bool, optional
        Append the UTC time zone information to the resulting timestamp.
        The default is True.

    Returns
    -------
    now_is : str
        The current time in a formated string.
    """
    now = time.localtime()
    ymd = time.strftime(ymd_directive, now)
    if is_ymd_wo_leading_zeros:
        ymd_wo_leading_zeros = [s.lstrip('0') for s in ymd.split(' ')]
        ymd = ' '.join(ymd_wo_leading_zeros)
    hms = time.strftime(hms_directive, now)
    now_is = '{}{} {}{}'.format(ymd_preposition, ymd, hms_preposition, hms)
    if is_append_utc:
        utc = re.sub('([0-9]{2})([0-9]{2})', r'\1:\2',
                     time.strftime('%z', now))
        now_is += ' (UTC{})'.format(utc)
    return now_is


def get_target_sum(tgt_sum, objs, r,
                   unc=0):
    """Find a target sum from a pool of candidates using brute-force search.

    Parameters
    ----------
    tgt_sum : float
        A target sum of interest.
    objs : list
        A list of candidate objects.
    r : int
        The number of choosing objects.
    unc : float, optional
        Uncertainty of the brute-force search. The default is 0.

    Returns
    -------
    combos : list
        Combinations of objects leading to the target sum within
        the limit of uncertainty.
    """
    combos = [combo for combo in combinations(objs, r)
              if abs(sum(combo) - tgt_sum) <= unc]
    return combos


def merge(destination, source):
    """Deeply merge two dictionaries.

    Parameters
    ----------
    destination : dict
        A dictionary into which another dictionary will be deeply merged.
    source : dict
        A dictionary to be deeply merged to another.

    Returns
    -------
    destination : dict
        A deeply merged dictionary.

    Notes
    -----
    This function was inspired by the one posted at:
    https://stackoverflow.com/a/20666342
    """
    for k, v in source.items():
        if isinstance(v, dict):
            node = destination.setdefault(k, {})
            merge(node, v)
        else:
            destination[k] = v
    return destination


def pause_shell(second):
    """Pause the shell during the designated time expressed in second.

    Parameters
    ----------
    sec : int
        The waiting time expressed in second.

    Returns
    -------
    None.
    """
    second = int(second)
    for remaining in range(second, 0, -1):
        sys.stdout.write('\r')
        sys.stdout.write(f'Waiting for [{remaining} s]...')
        sys.stdout.flush()
        time.sleep(1)


def invoke_yn_prompt(msg='Run (y/n)? '):
    """Invoke a y/n selection prompt.

    Parameters
    ----------
    msg : str, optional
        A message displayed with the y/n selection prompt.
        The default is 'Run (y/n)? '.

    Returns
    -------
    is_y : bool
        True for the user input of 'y' or Y', and False for 'n' or 'N'.
    """
    is_y = False
    while True:
        yn = input(msg)
        if not re.search(r'(?i)\b\s*[yn]\s*\b', yn):
            continue
        if re.search(r'(?i)y', yn):
            is_y = True
        break
    return is_y


def centering(s,
              ref_len=70):
    """Center a string with respect to a user-specified string length.

    Parameters
    ----------
    s : str
        A string to be centered.
    ref_len : int, optional
        A user-specified length; half this value will be used as
        the number of leading spaces. The default is 70.

    Returns
    -------
    s_centered : str
        A centered string.
    """
    s_centered = ' ' * int((ref_len - len(s)) / 2) + s
    return s_centered


def show_msg(msg,
             border_symb='-', is_bordered=False, is_centered=False):
    """Display a message with an optional pair of display borders.

    Parameters
    ----------
    msg : str
        A message to be displayed
    border_symb : str, optional
        The symbol for display borders. The default is '-'.
    is_bordered : bool, optional
        If True, the message will be enclosed by a pair of display borders.
        The default is False.
    is_centered : bool, optional
        If True, the message will be centered. The default is False.

    Returns
    -------
    None.
    """
    the_msg = centering(msg) if is_centered else msg
    if is_bordered:
        print(BORDERS[border_symb])
    print(the_msg)
    if is_bordered:
        print(BORDERS[border_symb])


def show_warn(msg):
    """Display a warning message with a pair of display borders.

    Parameters
    ----------
    msg : str
        A warning message to be displayed.

    Returns
    -------
    None.
    """
    show_msg(msg,
             border_symb='*', is_bordered=True, is_centered=True)


def show_front_matter(prog_info,
                      is_prog=True, is_auth=True):
    """Display a program front matter.

    Parameters
    ----------
    prog_info : dict
        Program and author information
    is_prog : bool, optional
        Display the program information. The default is True.
    is_auth : bool, optional
        Display the author information. The default is True.

    Returns
    -------
    None.
    """
    msg = ''
    if is_prog:
        py_ver = re.sub('^([0-9.]+).*', r'\1', sys.version)
        prog_info_msg = [
            '{}: {}'.format(prog_info['name'], prog_info['desc']),
            '{} v{} ({})'.format(prog_info['name'], prog_info['vers'],
                                 prog_info['date']),
            'running on Python v{}'.format(py_ver),
            get_now(),
        ]
        centered = [centering(s) for s in prog_info_msg]
        msg += '\n'.join(centered)
    if is_auth:
        if is_prog:
            msg += '\n\n'  # Insert a blank line between prog and auth.
        centered = [centering(v) for v in prog_info['auth'].values()]
        msg += '\n'.join(centered)
    show_msg(msg,
             border_symb='+', is_bordered=True)


get_borders()
if __name__ == '__main__':
    show_warn('You are running me directly.')
