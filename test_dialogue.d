// Test D file for speaker analysis

BEGIN ~TEST_MINSC~

CHAIN
  == MINSCJ
    ~Boo says we should help this person!~
    =
    ~Yes, Boo is very wise about these things.~
  == IMOEN2J
    ~I think your hamster might be right, Minsc.~
  == MINSCJ
    ~Of course he is right! Boo is always right!~
EXIT

INTERJECT_COPY_TRANS PLAYER1 25 MyInterject
  == KORGANJ
    ~This looks dangerous. I suggest we proceed carefully.~
  == JAHEIRAJ  
    ~Nature will guide our path.~
END

EXTEND_TOP ~NALIA~ 1
  == NALIAJ
    ~As a noble, I feel obligated to help.~
  == ANOMENJ
    ~Justice demands we act.~
END