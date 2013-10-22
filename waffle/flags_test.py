from injector import Injector, Module

from .flags import FlagsModule, Flag, FlagKey


class TestModule(Module):
    flag1 = Flag('--flag1', default=1, type=int)
    flag2 = Flag('--flag2', type=int)

    def configure(self, binder):
        assert self.flag1 == 1
        assert self.flag2 == 2


def test_flag():
    injector = Injector([FlagsModule(['test'], {'flag2': 2}), TestModule()])
    assert injector.get(FlagKey('flag1')) == 1
    assert injector.get(FlagKey('flag2')) == 2
