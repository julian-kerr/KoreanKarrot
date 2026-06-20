from hangul_romanize import Transliter
from hangul_romanize.rule import academic

Transliter = Transliter(academic)

print(Transliter.translit("진짜"))
print(Transliter.translit("먹다"))
print(Transliter.translit("학교"))