lexer grammar DLexer;

WHITESPACE
:
    [ \r\n\t]+ -> skip
;


// lexer grammar Comments;


LINE_COMMENT
:
    '/' '/' ~[\n]* -> skip
;

BLOCK_COMMENT_START
:
    '/*' -> pushMode ( BLOCK_COMMENT_MODE ) , more
;

mode BLOCK_COMMENT_MODE;

// XXX: Weidu allows nested block comments

BLOCK_COMMENT_NEST
:
    '/*' -> pushMode ( BLOCK_COMMENT_MODE ) , more
;

BLOCK_COMMENT_CHAR
:
    . -> more
;

BLOCK_COMMENT_END
:
    '*/' -> popMode , skip
;

UNTERMINATED_BLOCK_COMMENT
:
    EOF -> popMode
;


mode DEFAULT_MODE;

// lexer grammar DKeywords;

BEGIN
:
    'BEGIN'
;

END
:
    'END'
;

IF
:
    'IF'
;

UNLESS
:
    'UNLESS'
;

WEIGHT
:
    'WEIGHT'
;

THEN
:
    'THEN'
;

EQ
:
    '='
;

EQEQ
:
    '=='
;

BRANCH
:
    'BRANCH'
;

PLUS
:
    '+'
;

COPY_TRANS
:
    'COPY_TRANS'
;

COPY_TRANS_LATE
:
    'COPY_TRANS_LATE'
;

DO
:
    'DO'
;

JOURNAL
:
    'JOURNAL'
;

SOLVED_JOURNAL
:
    'SOLVED_JOURNAL'
;

UNSOLVED_JOURNAL
:
    'UNSOLVED_JOURNAL'
;

FLAGS
:
    'FLAGS'
;

GOTO
:
    'GOTO'
;

APPENDI
:
    'APPENDI'
;

CHAIN2
:
    'CHAIN2'
;

SAFE
:
    'SAFE'
;

EXTERN
:
    'EXTERN'
;

REPLY
:
    'REPLY'
;

EXIT
:
    'EXIT'
;

SAY
:
    'SAY'
;

IF_FILE_EXISTS
:
    'IF_FILE_EXISTS'
;

PAREN_OPEN
:
    '('
;

PAREN_CLOSE
:
    ')'
;

AT
:
    'AT'
;

APPEND
:
    'APPEND'
;

APPEND_EARLY
:
    'APPEND_EARLY'
;

CHAIN
:
    'CHAIN'
    | 'CHAIN3'
;

INTERJECT
:
    'INTERJECT'
;

EXTEND_TOP
:
    'EXTEND_TOP'
;

ADD_STATE_TRIGGER
:
    'ADD_STATE_TRIGGER'
    | 'A_S_T'
;

ADD_TRANS_TRIGGER
:
    'ADD_TRANS_TRIGGER'
    | 'A_T_T'
;

ADD_TRANS_ACTION
:
    'ADD_TRANS_ACTION'
;

REPLACE_TRANS_ACTION
:
    'REPLACE_TRANS_ACTION'
;

REPLACE_TRANS_TRIGGER
:
    'REPLACE_TRANS_TRIGGER'
;

ALTER_TRANS
:
    'ALTER_TRANS'
;

REPLACE
:
    'REPLACE'
;

SET_WEIGHT
:
    'SET_WEIGHT'
;

REPLACE_STATE_TRIGGER
:
    'REPLACE_STATE_TRIGGER'
    | 'R_S_T'
;

REPLACE_TRIGGER_TEXT
:
    'REPLACE_TRIGGER_TEXT'
    | 'R_T_T'
;

REPLACE_TRIGGER_TEXT_REGEXP
:
    'REPLACE_TRIGGER_TEXT_REGEXP'
;

REPLACE_ACTION_TEXT
:
    'REPLACE_ACTION_TEXT'
    | 'R_A_T'
;

REPLACE_ACTION_TEXT_REGEXP
:
    'REPLACE_ACTION_TEXT_REGEXP'
;

REPLACE_ACTION_TEXT_PROCESS
:
    'REPLACE_ACTION_TEXT_PROCESS'
;

REPLACE_ACTION_TEXT_PROCESS_REGEXP
:
    'R_A_T_P_R'
    | 'REPLACE_ACTION_TEXT_PROCESS_REGEXP'
;

REPLACE_SAY
:
    'REPLACE_SAY'
;

EXTEND_BOTTOM
:
    'EXTEND_BOTTOM'
    | 'EXTEND'
;

INTERJECT_COPY_TRANS
:
    'INTERJECT_COPY_TRANS'
    | 'I_C_T'
;

INTERJECT_COPY_TRANS2
:
    'INTERJECT_COPY_TRANS2'
    | 'I_C_T2'
;

INTERJECT_COPY_TRANS3
:
    'INTERJECT_COPY_TRANS3'
    | 'I_C_T3'
;

INTERJECT_COPY_TRANS4
:
    'INTERJECT_COPY_TRANS4'
    | 'I_C_T4'
;


// lexer grammar Fragments;

fragment
LETTER
:
    [a-zA-Z]
;

fragment
ALPHANUM
:
    LETTER
    | DEC_DIGIT
;

fragment
BIN_DIGIT
:
    [01]
;

fragment
OCT_DIGIT
:
    [0-7]
;

fragment
DEC_DIGIT
:
    [0-9]
;

fragment
HEX_DIGIT
:
    DEC_DIGIT
    | [a-fA-F]
;

fragment
OCT_LITERAL_PREFIX
:
    '0o'
;

fragment
BIN_LITERAL_PREFIX
:
    '0b'
;

fragment
HEX_LITERAL_PREFIX
:
    '0x'
;
    
    
    //lexer grammar Ids;


IDENTIFIER
:
    (
        ALPHANUM
        | '_'
    )
    (
        ALPHANUM
        | '-'
        | '_'
        | '#'
        | '.'
        | '\''
    )*
;

// lexer grammar Numbers;


SHARP_NUMBER
:
    '#' '-'? DEC_DIGIT+
;

//lexer grammar Strings;

SOUND_STRING
:
    '['
    (
        .
    )*? ']'
;

TILDE_STRING
:
    '~'
    (
        .
    )*? '~'
;

QUOTE_STRING
:
    '"'
    (
        .
    )*? '"'
;

PERCENT_STRING
:
    '%'
    (
        .
    )*? '%'
;

FORCED_STRING_REFERENCE
:
    '!' [0-9]+
;

TRANSLATION_REFERENCE
:
    '@' [0-9]+
;

CONCAT
:
    '^'
;

LONG_TILDE_STRING_START
:
    '~~~~~' -> pushMode ( LONG_TILDE_STRING_MODE ), more
;

mode LONG_TILDE_STRING_MODE;

LONG_TILDE_STRING_BODY
:
    . -> more
;

LONG_TILDE_STRING
:
    '~~~~~' -> popMode
;

LONG_TILDE_STRING_UNTERMINATED
:
    EOF -> popMode
;