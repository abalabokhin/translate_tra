BEGIN L#IGB3E

CHAIN IF ~Global("L#IGB3StartBattle","GLOBAL",0)~ THEN L#IGB3E 000
@0
DO ~SetGlobal("L#IGB3StartBattle","GLOBAL",1) Enemy()~ EXIT