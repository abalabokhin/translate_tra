BEGIN L#IGB2

//INCOMPLETE

CHAIN IF ~Global("L#IGBook2","GLOBAL",0)~ THEN L#IGB2 100
@0
== L#IGB2 @1
==YoshJ IF ~InParty("Yoshimo") !StateCheck("Yoshimo",CD_STATE_NOTVALID) !PartyHasItem("SW1H51")~ THEN @2
==YoshJ IF ~InParty("Yoshimo") !StateCheck("Yoshimo",CD_STATE_NOTVALID) PartyHasItem("SW1H51")~ THEN @3
==L#IGSTA @4
END
IF~PartyGoldGT(3499)~THEN REPLY @5 DO ~TakePartyGold(3500) DestroyGold(3500)~ EXTERN L#IGSTA 101
IF~~THEN REPLY @6 EXIT

CHAIN L#IGSTA 101
@7
DO ~SetGlobal("L#IGBook2","GLOBAL",1)~ EXIT

//COMPLETED

CHAIN IF ~Global("L#IGBook2","GLOBAL",2)~ THEN L#IGB2 200
@8
==L#IGB1 @9
END
IF~~THEN REPLY @10 EXTERN L#IGB2 201
IF~~THEN REPLY @11 EXTERN L#IGB2 201b

CHAIN L#IGB2 201
@12
END
IF~Exists(Player1)~THEN REPLY @13 DO ~SetGlobal("L#IGBook2RewPla1","GLOBAL",1)~ EXTERN L#IGB2 202
IF~Exists(Player2)~THEN REPLY @14 DO ~SetGlobal("L#IGBook2RewPla2","GLOBAL",1)~ EXTERN L#IGB2 202
IF~Exists(Player3)~THEN REPLY @15 DO ~SetGlobal("L#IGBook2RewPla3","GLOBAL",1)~ EXTERN L#IGB2 202
IF~Exists(Player4)~THEN REPLY @16 DO ~SetGlobal("L#IGBook2RewPla4","GLOBAL",1)~ EXTERN L#IGB2 202
IF~Exists(Player5)~THEN REPLY @17 DO ~SetGlobal("L#IGBook2RewPla5","GLOBAL",1)~ EXTERN L#IGB2 202
IF~Exists(Player6)~THEN REPLY @18 DO ~SetGlobal("L#IGBook2RewPla6","GLOBAL",1)~ EXTERN L#IGB2 202

CHAIN L#IGB2 201b
@19
END
IF~Exists(Player1)~THEN REPLY @13 DO ~SetGlobal("L#IGBook2RewPla1b","GLOBAL",1)~ EXTERN L#IGB2 202b
IF~Exists(Player2)~THEN REPLY @14 DO ~SetGlobal("L#IGBook2RewPla2b","GLOBAL",1)~ EXTERN L#IGB2 202b
IF~Exists(Player3)~THEN REPLY @15 DO ~SetGlobal("L#IGBook2RewPla3b","GLOBAL",1)~ EXTERN L#IGB2 202b
IF~Exists(Player4)~THEN REPLY @16 DO ~SetGlobal("L#IGBook2RewPla4b","GLOBAL",1)~ EXTERN L#IGB2 202b
IF~Exists(Player5)~THEN REPLY @17 DO ~SetGlobal("L#IGBook2RewPla5b","GLOBAL",1)~ EXTERN L#IGB2 202b
IF~Exists(Player6)~THEN REPLY @18 DO ~SetGlobal("L#IGBook2RewPla6b","GLOBAL",1)~ EXTERN L#IGB2 202b

CHAIN L#IGB2 202
@20
DO ~SetGlobal("L#IGBook2","GLOBAL",3)~ EXIT

CHAIN L#IGB2 202b
@20
DO ~SetGlobal("L#IGBook2","GLOBAL",3)~ EXIT

CHAIN IF ~Global("L#IGBook2","GLOBAL",4)~ THEN L#IGB2 300
@21
EXIT