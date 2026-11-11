BEGIN L#IGB7E

CHAIN IF ~Global("L#IGB7StartBattle","GLOBAL",0)~ THEN L#IGB7E 000
@0
DO ~SetGlobal("L#IGB7StartBattle","GLOBAL",1) Enemy()~ EXIT