BEGIN L#IGB1E

CHAIN IF ~Global("L#IGB1StartBattle","GLOBAL",0)~ THEN L#IGB1E 000
@0
==L#IGB1E @1
DO ~SetGlobal("L#IGB1StartBattle","GLOBAL",1) Enemy()~ EXIT