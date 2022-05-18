from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Foo:
    ivar: float = 0.5
    cvar: ClassVar[float] = 0.3
    nvar = 0.5


foo = Foo()
Foo.ivar, Foo.cvar, Foo.nvar = 1, 1, 1
Foo.cvar = 22.2
foo.cvar = 33
print(Foo().ivar, Foo().cvar, Foo().nvar)  # 0.5 1 1
print(foo.ivar, foo.cvar, foo.nvar)  # 0.5 1 1
