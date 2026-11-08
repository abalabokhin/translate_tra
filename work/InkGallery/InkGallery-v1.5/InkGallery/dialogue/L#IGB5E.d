BEGIN L#IGB5E

CHAIN IF ~Global("L#IGB5StartBattle","GLOBAL",0)~ THEN L#IGB5E 000
@0
DO ~SetGlobal("L#IGB5StartBattle","GLOBAL",1) ApplySpell(Myself,WIZARD_STONE_SKIN) Enemy()~ EXIT