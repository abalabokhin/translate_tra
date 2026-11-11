BEGIN L#IGB9E

CHAIN IF ~Global("L#IGB9StartBattle","GLOBAL",0)~ THEN L#IGB9E 000
@0
DO ~SetGlobal("L#IGB9StartBattle","GLOBAL",1) Enemy()~ EXIT