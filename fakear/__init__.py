import os
import yaml

from shutil import rmtree, copyfile
from subprocess import run
from voluptuous import Schema, Required, Optional, Exclusive, Match, Any, ALLOW_EXTRA
from fakear import templates

class FakearMultipleSourceException(Exception):
    pass

class Fakear(object):

    validate_file = Schema({
        Match(r'^[A-Za-z0-9]+$'): Any(list, None)
    }, extra=ALLOW_EXTRA)

    validate_args = Schema([{
            Optional('args'): list,
            Required('return_code'): int,
            Exclusive('output', 'output'): str,
            Exclusive('output_file', 'output'): str
        }] )

    def __init__(self, cfg=None, rawdata=None):
        self.__fakedcmds = {}
        self.__enabled = False
        self.__faked_path = "/tmp/fakear/binaries"
        self.__cfg_paths = []
        self.__shell = self.__search_for_interpreter()

        if all([not cfg, not rawdata]): return
        if all([cfg, rawdata]):
            raise FakearMultipleSourceException()
        if cfg:
            rawdata = self.__add_configuration(cfg)

        data = self.validate_file(yaml.load(rawdata))
        self.__load_fake_cmds(data)

    ## Properties

    @property
    def commands(self):
        """
        Returns a dict with all faked programs embedded in this Fakear instance
        Can be set at instantiation
        """
        return self.__fakedcmds

    @property
    def faked_path(self):
        """
        Returns the path used to store fake programs generated by Fakear
        Default is: /tmp/fakear/binaries

        Use self.set_fake_path() to set another path
        """
        return self.__faked_path

    @property
    def shell(self):
        """
        Returns the shell path Fakear will use for making fake programs
        """
        return self.__shell


    ## Private method

    def __search_for_interpreter(self):
        p = run(["which", "bash"], capture_output=True)
        return p.stdout.decode().replace("\n", "")

    
    def __load_fake_cmds(self, data):
        for cmd, args in data.items():
            if args:
                self.__fakedcmds[cmd] = self.validate_args(args) 
            else:
                self.__fakedcmds[cmd] = []
    def __add_configuration(self, filepath):
        if "/" in filepath:
            path = "/".join(filepath.split("/")[:-1])
            self.__cfg_paths.append(path)
        with open(filepath) as d:
            rawdata = d.read()
            return rawdata


    def __search_for_file(self, filepath):
        for path in self.__cfg_paths:
            tmp_path = os.path.join(path, filepath)
            if os.path.exists(tmp_path):
                return tmp_path

        return None


    def __write_binaries(self):
        for command, subcmds in self.__fakedcmds.items():
            subs = sorted(subcmds, key=lambda a: len(a.get('args', [])), reverse=True)
            filepath = os.path.join(self.faked_path, command)
            binary = []

            # Case for no subcommand
            if not subs:
                binary.append(templates.sh_default)
            else:
                for sub in subs:
                    sub_extract = sub.get('args', [])
                    zipped_subs = list(zip(range(1, len(sub_extract) + 1), sub_extract))

                    sub_args = {
                        'length': len(zipped_subs),
                        'arg_line': " && ".join([ f'"${a[0]}" = "{a[1]}"' for a in zipped_subs ])
                    }

                    if sub_args['arg_line']:
                        if not binary:
                            binary.append(templates.sh_if.format(**sub_args))
                        else:
                            binary.append(templates.sh_elif.format(**sub_args))
                    else:
                        if len(binary):
                            binary.append(templates.sh_else)

                    if "output_file" in sub.keys():
                        output_path = os.path.join( self.__faked_path, f"{command}_files")
                        if not os.path.exists( output_path ):
                            os.makedirs( output_path )
                        if sub.get('output_file', None):
                            src_filepath = self.__search_for_file(sub['output_file'])
                            src_filename = src_filepath.split("/")[-1]
                            sub['output_file'] = os.path.join( output_path, src_filename )
                            copyfile(src_filepath, sub['output_file'])
                            binary.append(templates.sh_output_file.format(**sub))
                    else:
                        binary.append(templates.sh_output.format(**sub))                        
                        
            if len(binary) > 1:
                binary.append(templates.sh_fi)

            with open(filepath, 'w+') as f:
                f.writelines(templates.sh_header.format(shell_path=self.__shell))
                f.writelines(binary)

            os.chmod(filepath, 0o777)


    def __enable_path(self):
        if self.__faked_path not in os.environ["PATH"]:
            os.environ["PATH"] = f'{self.__faked_path}:{os.environ["PATH"]}'
            

    def __disable_path(self):
        if self.__faked_path in os.environ["PATH"]:
            path = ":".join([
                p for p in os.environ["PATH"].split(":")
                    if self.__faked_path not in p
            ])
            os.environ['PATH'] = path



    ## API

    def set_faked_path(self, path):
        if not self.__enabled:
            self.__faked_path = path
            

    def enable(self):
        if not os.path.exists(self.__faked_path):
            os.makedirs(self.__faked_path)
        self.__write_binaries()
        self.__enable_path()
        self.__enabled = True

    def disable(self):
        if os.path.exists(self.__faked_path):
            rmtree(self.__faked_path)
        self.__disable_path()
        self.__enabled = False        
