BEGIN L#IGB9

//INCOMPLETE

CHAIN IF ~Global("L#IGBook9","GLOBAL",0)~ THEN L#IGB9 100
@0
==ANOMENJ IF ~InParty("ANOMEN") !StateCheck("ANOMEN",CD_STATE_NOTVALID)~ THEN @1
==L#IGSTA @2
END
IF~PartyGoldGT(2999) Exists(Player1) !StateCheck(Player1,STATE_DEAD) !StateCheck(Player1,STATE_REALLY_DEAD) !StateCheck(Player1,STATE_ACID_DEATH) !StateCheck(Player1,STATE_FLAME_DEATH) !StateCheck(Player1,STATE_EXPLODING_DEATH) !StateCheck(Player1,STATE_STONE_DEATH) !StateCheck(Player1,STATE_FROZEN_DEATH)~THEN REPLY @3 DO ~TakePartyGold(3500) DestroyGold(3500) SetGlobal("L#IGBook9RewPla1","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~PartyGoldGT(2999) Exists(Player2) !StateCheck(Player2,STATE_DEAD) !StateCheck(Player2,STATE_REALLY_DEAD) !StateCheck(Player2,STATE_ACID_DEATH) !StateCheck(Player2,STATE_FLAME_DEATH) !StateCheck(Player2,STATE_EXPLODING_DEATH) !StateCheck(Player2,STATE_STONE_DEATH) !StateCheck(Player2,STATE_FROZEN_DEATH)~THEN REPLY @4 DO ~TakePartyGold(3000) DestroyGold(3000) SetGlobal("L#IGBook9RewPla2","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~PartyGoldGT(2999) Exists(Player3) !StateCheck(Player3,STATE_DEAD) !StateCheck(Player3,STATE_REALLY_DEAD) !StateCheck(Player3,STATE_ACID_DEATH) !StateCheck(Player3,STATE_FLAME_DEATH) !StateCheck(Player3,STATE_EXPLODING_DEATH) !StateCheck(Player3,STATE_STONE_DEATH) !StateCheck(Player3,STATE_FROZEN_DEATH)~THEN REPLY @5 DO ~TakePartyGold(3000) DestroyGold(3000) SetGlobal("L#IGBook9RewPla3","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~PartyGoldGT(2999) Exists(Player4) !StateCheck(Player4,STATE_DEAD) !StateCheck(Player4,STATE_REALLY_DEAD) !StateCheck(Player4,STATE_ACID_DEATH) !StateCheck(Player4,STATE_FLAME_DEATH) !StateCheck(Player4,STATE_EXPLODING_DEATH) !StateCheck(Player4,STATE_STONE_DEATH) !StateCheck(Player4,STATE_FROZEN_DEATH)~THEN REPLY @6 DO ~TakePartyGold(3000) DestroyGold(3000) SetGlobal("L#IGBook9RewPla4","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~PartyGoldGT(2999) Exists(Player5) !StateCheck(Player5,STATE_DEAD) !StateCheck(Player5,STATE_REALLY_DEAD) !StateCheck(Player5,STATE_ACID_DEATH) !StateCheck(Player5,STATE_FLAME_DEATH) !StateCheck(Player5,STATE_EXPLODING_DEATH) !StateCheck(Player5,STATE_STONE_DEATH) !StateCheck(Player5,STATE_FROZEN_DEATH)~THEN REPLY @7 DO ~TakePartyGold(3000) DestroyGold(3000) SetGlobal("L#IGBook9RewPla5","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~PartyGoldGT(2999) Exists(Player6) !StateCheck(Player6,STATE_DEAD) !StateCheck(Player6,STATE_REALLY_DEAD) !StateCheck(Player6,STATE_ACID_DEATH) !StateCheck(Player6,STATE_FLAME_DEATH) !StateCheck(Player6,STATE_EXPLODING_DEATH) !StateCheck(Player6,STATE_STONE_DEATH) !StateCheck(Player6,STATE_FROZEN_DEATH)~THEN REPLY @8 DO ~TakePartyGold(3000) DestroyGold(3000) SetGlobal("L#IGBook9RewPla6","GLOBAL",1) SetGlobal("L#IGBook9","GLOBAL",1)~ EXTERN L#IGSTA 101
IF~~THEN REPLY @9 EXIT

CHAIN L#IGSTA 101
@10
EXIT

//COMPLETED

CHAIN IF ~Global("L#IGBook9","GLOBAL",2) Global("L#IGBook9Finished","GLOBAL",1)~ THEN L#IGB9 200
@11
==L#IGB9 @12
DO ~SetGlobal("L#IGBook9","GLOBAL",3)~ EXIT

CHAIN IF ~Global("L#IGBook9","GLOBAL",4)~ THEN L#IGB9 300
@13
EXIT