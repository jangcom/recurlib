#!/usr/bin/env python3
"""inpout: A custom I/O interface

Classes
-------
InpOut()
    A file I/O interface class
"""

import os
import sys
import re
import argparse
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

__author__ = 'Jaewoong Jang'
__copyright__ = 'Copyright (c) 2024 Jaewoong Jang'
__license__ = 'MIT License'
__version__ = '1.0.0'
__date__ = '2024-04-28'


class InpOut():
    """A file I/O interface class.

    Parameters
    ----------
    conf_file_type : str
        The type of a program configuration file.

    Attributes
    ----------
    conf_file_type : str
        The type of a program configuration file.

    Methods
    -------
    read_argv(desc='')
        Read the sys.argv list into a program.
    show_file_gen(fname, verb=' generated.')
        Notify the creation of a file or a directory.
    dump_yaml(yml_d,
              msg='', is_savetxt=False, txt_fname_full='./yaml_dump.txt')
        Dump the content of a dictionary possibly generated via YAML.
    read_yaml(yml, yml_encoding='utf-8', is_yml_required=True, is_echo=False)
        Read a YAML file into a dictionary.
    get_fname_full(dname, fname)
        Join the names of a directory and a file.
    mk_dir(dname)
        Create a directory if it does not exist.
    locate_exe(v, re_exe)
        Locate an executable from the path environment variable.
    save_df(df, pname, bname, fmts='xlsx')
        Save a pandas DataFrame to multiple file formats.
    save_jinja(context, tpl_fname_full, out_pname, out_bname,
               out_encoding='utf-8')
        Render a Jinja template to an output file.
    """

    def __init__(self,
                 conf_file_type='.yml'):
        """Initialize an object of the InpOut class.

        Parameters
        ----------
        conf_file_type : str, optional
            The type of a program configuration file. The default is '.yml'.

        Returns
        -------
        None.
        """
        self.conf_file_type = conf_file_type

    def read_argv(self,
                  desc='', ini_dflt='ini.yaml'):
        """Read the sys.argv list into a program.

        Parameters
        ----------
        desc : str, optional
            A description of argparse.ArgumentParser. The default is ''.
        ini : str, optional
            A low-level initialization file. The default is 'ini.yaml'.

        Returns
        -------
        argparse.Namespace
            The Namespace object of argparse.
        """
        parser = argparse.ArgumentParser(
            description=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('file',
                            help='a program configuration file ({})'.format(
                                self.conf_file_type))
        parser.add_argument('--ini',
                            default=ini_dflt,
                            help='a low-level configuration file ({})'.format(
                                self.conf_file_type))
        parser.add_argument('--echo',
                            dest='is_echo',
                            action='store_true',
                            help='echo the YAML content on the shell')
        return parser.parse_args()

    def show_file_gen(self, fname,
                      verb=' generated.'):
        """Notify the creation of a file or a directory.

        Parameters
        ----------
        fname : str
            The name of a file or directory whose creation is to be notified.
        verb : str, optional
            A verb describing the creation of a file or directory.
            The default is ' generated.'.

        Returns
        -------
        None.
        """
        fname = re.sub(r'\\', '/', fname)  # Show a consistent path separator.
        msg = f'[{fname}]{verb}'
        mt.show_msg(msg)

    def dump_yaml(self, yml_d,
                  yml_encoding='utf-8', msg='', is_savetxt=False,
                  txt_fname_full='./yaml_dump.txt'):
        """Dump the content of a dictionary possibly generated via YAML.

        Parameters
        ----------
        yml_d : dict
            A dictionary whose content is to be printed.
        msg : str, optional
            If not None, this string will be printed as a header before
            the YAML content. The default is ''.
        is_savetxt : bool, optional
            If True, the print command will be directed to an output file
            instead of stdout. The default is False.
        txt_fname_full : str, optional
            A full-path file name for is_savetxt == True.
            The default is './yaml_dump.txt'.

        Returns
        -------
        None.
        """
        if is_savetxt:
            with open(txt_fname_full, 'w', encoding=yml_encoding) as out_fh:
                if msg:
                    out_fh.write(msg)
                out_fh.write(yaml.dump(yml_d,
                                       sort_keys=False))
            self.show_file_gen(txt_fname_full)
        else:
            if msg:
                mt.show_msg(msg,
                            border_symb='-',
                            is_bordered=True,
                            is_centered=True)
            print(yaml.dump(yml_d,
                            sort_keys=False))

    def read_yaml(self, yml,
                  yml_encoding='utf-8', is_yml_required=True, is_echo=False):
        """Read a YAML file into a dictionary.

        Parameters
        ----------
        yml : str
            A YAML file to be read in.
        yml_encoding : str, optional
            The encoding of the YAML file. The default is 'utf-8'.
        is_yml_required : bool, optional
            If True, exit the program if the designated YAML file was not
            found. The default is True.
        is_echo : bool, optional
            If True, dump the content of the YAML file. The default is False.

        Returns
        -------
        yml_d : dict
            A dictionary containing the content of the YAML file
        """
        if not os.path.exists(yml):
            msg = f'The designated YAML file [{yml}] could not be located.'
            mt.show_warn(msg)
            if is_yml_required:
                print(' Terminating.')
                sys.exit()
        with open(yml, 'r', encoding=yml_encoding) as fh:
            yml_d = yaml.load(fh, Loader=yaml.FullLoader)
        if is_echo:
            msg = f'Content of [{yml}]'
            self.dump_yaml(yml_d,
                           msg=msg)
        return yml_d

    def get_fname_full(self, dname, fname):
        """Join the names of a directory and a file.

        Parameters
        ----------
        dname : str
            The name of a directory.
        fname : str
            The name of a file.

        Returns
        -------
        fname_full : str
            A constructed full-path file name.
        """
        fname = os.path.basename(fname)
        fname_full = '{}/{}'.format(dname, fname)
        return fname_full

    def mk_dir(self, dname,
               is_yn=True):
        """Create a directory if not exist.

        Parameters
        ----------
        dname : str
            The name of a directory to be created.
        is_yn : bool, optional
            If True, invoke a y/n prompt. The default is True.

        Returns
        -------
        None.
        """
        dname = re.sub(r'\\', '/', dname)  # Use a consistent path separator.
        if not os.path.exists(dname):
            is_mk_dir = True  # Forcible directory creation for is_yn == False
            if is_yn:
                q = (f'The designated directory [{dname}] not found.'
                     + ' Create (y/n)? ')
                is_mk_dir = mt.invoke_yn_prompt(q)
            if is_mk_dir:
                os.mkdir(dname)
                self.show_file_gen(dname)

    def locate_exe(self, v, re_exe):
        """Locate an executable from the path environment variable.

        Parameters
        ----------
        v : str
            A regex for the path of a directory containing the executable
            of interest stored in the 'path' environment variable.
        re_exe : str
            A regex for the file name of the executable.

        Returns
        -------
        the_located_exe : str
            The file name of the located executable.
        """
        the_located_exe = ''
        path_vals = re.split(';', os.environ['path'])
        for path_val in path_vals:
            if re.search(v, path_val):
                fnames_in_the_found_path = os.listdir(path_val)
                for fname in fnames_in_the_found_path:
                    if re.search(re_exe, fname):
                        the_located_exe = fname
                        break
        return the_located_exe

    def save_df(self, df, pname, bname,
                fmt='xlsx', xl_sheet_name='library', xml_parser='etree'):
        """Save a pandas DataFrame to multiple file formats.

        Parameters
        ----------
        df : pandas.core.frame.DataFrame
            A DF of interest for file saiving.
        pname : str
            The path to which files will be saved.
        bname : str
            The base name of files to be saved.
        fmt : str, optional
            The file format to be saved. The default is 'xlsx'.
        xl_sheet_name : str, optional
            The sheet name of an output Excel file. The default is 'library'.
        xml_parser : str, optional
            A parser of df.to_xml(). The default is 'etree'.

        Returns
        -------
        None.
        """
        cmds = {
            'csv': {
                'method': getattr(df, 'to_csv'),
            },
            'html': {
                'method': getattr(df, 'to_html'),
            },
            'xml': {
                'method': getattr(df, 'to_xml'),
                'kwargs': dict(index=False, parser=xml_parser),
            },
            'tex': {
                'method': getattr(df, 'to_latex'),
            },
            'xlsx': {
                'method': getattr(df.style.background_gradient(), 'to_excel'),
                'kwargs': dict(sheet_name=xl_sheet_name),
            },
        }
        kwargs_common = dict(encoding='utf8')
        if fmt not in cmds.keys():
            msg = f'The format [{fmt}] is not supported; skipping.'
            mt.show_warn(msg)
            return
        try:
            cmds[fmt]['kwargs'].update(kwargs_common)
        except KeyError:
            cmds[fmt]['kwargs'] = kwargs_common
        out_fname_full = f'{pname}/{bname}.{fmt}'
        if re.search('(?i)xlsx', fmt):
            try:
                cmds[fmt]['method'](out_fname_full,
                                    **cmds[fmt]['kwargs'])
            except ModuleNotFoundError as e:
                print('Excel writing failed: {}'.format(e))
                return
        else:
            cmds[fmt]['method'](out_fname_full,
                                **cmds[fmt]['kwargs'])
        self.show_file_gen(out_fname_full)

    def save_jinja(self, context, tpl_fname_full, out_pname, out_bname,
                   out_encoding='utf-8'):
        """Render a Jinja template to an output file.

        Parameters
        ----------
        context : dict
            A context dictionary for Jinja rendering.
        tpl_fname_full : str
            A full-path file name for a Jinja template.
        out_pname : str
            The path to which the rendered file will be saved.
        out_bname : str
            The base name of the rendered file.
        out_encoding : str, optional
            The encoding of the rendered file. The default is 'utf-8'.

        Returns
        -------
        None.
        """
        # Template validation
        if not os.path.exists(tpl_fname_full):
            msg = (f'The designated Jinja template file [{tpl_fname_full}]'
                   + ' could not be located; rendering will be skipped.')
            mt.show_warn(msg)
            return

        # I/O preprocessing
        tpl_dname, tpl_fname = os.path.split(tpl_fname_full)
        out_fname = f'{out_bname}_{tpl_fname}'
        out_fname_full = f'{out_pname}/{out_fname}'

        # Load the user-designated Jinja template.
        env = Environment(loader=FileSystemLoader(tpl_dname),
                          autoescape=select_autoescape())
        template = env.get_template(tpl_fname)
        with open(out_fname_full, mode='w',
                  encoding=out_encoding) as out_fh:
            out_fh.write(template.render(context))
            self.show_file_gen(out_fname_full)


if __name__ == '__main__':
    import mytoolkit as mt
    mt.show_warn('You are running me directly.')
    io = InpOut()
    argv = io.read_argv()
    the_yml = io.read_yaml(argv.file,
                           is_echo=True)

else:
    try:
        from modules import mytoolkit as mt
    except ModuleNotFoundError:
        import mytoolkit as mt
