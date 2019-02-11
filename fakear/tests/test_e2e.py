import pytest
import yaml
import os

from subprocess import run
from fakear import Fakear
from voluptuous import Error as VoluptuousError


class TestEndToEndFakear(object):
    def test_enable_basic_cmd(self):
        fe = Fakear(cfg="fakear/tests/cfgs/multiple_cmd_mult_args.yml")
        fe.enable()
        assert fe.faked_path in os.environ["PATH"]
        assert os.path.exists(fe.faked_path)
        assert os.path.exists(fe.faked_path + "/echo")
        assert os.path.exists(fe.faked_path + "/ls")
        
        
        p = run(["ls", "omelette", "du", "fromage"], capture_output=True)
        assert p.stdout.decode() == "Dexter ??\n"
        assert p.returncode == 4

    
    def test_disable_basic_cmd(self):
        fe = Fakear(cfg="fakear/tests/cfgs/multiple_cmd_mult_args.yml")
        fe.enable()
        assert fe.faked_path in os.environ["PATH"]
        assert os.path.exists(fe.faked_path)
        assert os.path.exists(fe.faked_path + "/echo")
        assert os.path.exists(fe.faked_path + "/ls")

        fe.disable()
        assert fe.faked_path not in os.environ["PATH"]
        assert not os.path.exists(fe.faked_path)