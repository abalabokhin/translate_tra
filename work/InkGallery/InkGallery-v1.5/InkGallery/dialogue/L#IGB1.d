BEGIN L#IGB1

//INCOMPLETE

CHAIN IF ~Global("L#IGBook1","GLOBAL",0)~ THEN L#IGB1 100
@0
== ViconiJ IF ~InParty("viconia") !StateCheck("viconia",CD_STATE_NOTVALID)~ THEN @1
== ViconiJ IF ~InParty("viconia") !StateCheck("viconia",CD_STATE_NOTVALID)~ THEN @2
==L#IGSTA @3
END
IF~PartyGoldGT(3499)~THEN REPLY @4 DO ~TakePartyGold(3500) DestroyGold(3500)~ EXTERN L#IGSTA 101
IF~~THEN REPLY @5 EXIT

CHAIN L#IGSTA 101
@6
DO ~SetGlobal("L#IGBook1","GLOBAL",1)~ EXIT

//COMPLETED

CHAIN IF ~Global("L#IGBook1","GLOBAL",2)~ THEN L#IGB1 200
@7
==L#IGB1 @8
END
IF~Exists(Player1)~THEN REPLY @9 DO ~SetGlobal("L#IGBook1RewPla1","GLOBAL",1)~ EXTERN L#IGB1 201
IF~Exists(Player2)~THEN REPLY @10 DO ~SetGlobal("L#IGBook1RewPla2","GLOBAL",1)~ EXTERN L#IGB1 201
IF~Exists(Player3)~THEN REPLY @11 DO ~SetGlobal("L#IGBook1RewPla3","GLOBAL",1)~ EXTERN L#IGB1 201
IF~Exists(Player4)~THEN REPLY @12 DO ~SetGlobal("L#IGBook1RewPla4","GLOBAL",1)~ EXTERN L#IGB1 201
IF~Exists(Player5)~THEN REPLY @13 DO ~SetGlobal("L#IGBook1RewPla5","GLOBAL",1)~ EXTERN L#IGB1 201
IF~Exists(Player6)~THEN REPLY @14 DO ~SetGlobal("L#IGBook1RewPla6","GLOBAL",1)~ EXTERN L#IGB1 201

CHAIN L#IGB1 201
@15
DO ~SetGlobal("L#IGBook1","GLOBAL",3)~ EXIT

CHAIN IF ~Global("L#IGBook1","GLOBAL",4)~ THEN L#IGB1 300
@16
EXIT
