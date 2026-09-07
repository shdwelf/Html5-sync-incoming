' =============================================================
'  PRESSKIT.BAS  -  Press Kit Reassembler: QBasic scene intro
'  Original homage in the spirit of classic 1990s intro screens.
'  Runs under QBasic / QuickBasic inside DOSBox:  QB PRESSKIT.BAS
' =============================================================
SCREEN 0
WIDTH 80, 25
COLOR 11
CLS

' --- boot header -------------------------------------------------
LOCATE 2, 24: PRINT "PRESS KIT REASSEMBLER"
LOCATE 3, 24: PRINT STRING$(26, "=")
COLOR 7
LOCATE 5, 2: PRINT "engine .... presskit.wasm   (XOR / ROT13 / Caesar)"
LOCATE 6, 2: PRINT "output .... classic DOS press-kit program (.COM/.DAT)"
LOCATE 7, 2: PRINT "content ... your variables, your text - original tool"

' --- the ascii-art "button" --------------------------------------
COLOR 14
LOCATE 10, 20: PRINT "+-----------------------------------------+"
LOCATE 11, 20: PRINT "|                                         |"
LOCATE 12, 20: PRINT "|   [ REASSEMBLE THE PRESS KIT. ]         |"
LOCATE 13, 20: PRINT "|   [ type the access code, then GO. ]     |"
LOCATE 14, 20: PRINT "|                                         |"
LOCATE 15, 20: PRINT "+-----------------------------------------+"

' --- dramatic little boot beep + scan ----------------------------
FOR i = 1 TO 3: SOUND 800 + i * 150, 2: NEXT i

' --- fake access gate (matches the .COM it generates) ------------
COLOR 11
LOCATE 18, 2: INPUT "ACCESS CODE > ", code$
IF LCASE$(code$) <> "opensaysme" AND LCASE$(code$) <> "release" THEN
    COLOR 12: LOCATE 20, 2: PRINT "*** ACCESS DENIED ***"
    SOUND 100, 8: SLEEP 2: END
END IF

COLOR 10
LOCATE 20, 2: PRINT "ACCESS GRANTED"
COLOR 7

' --- show the reassembled body text -------------------------------
LOCATE 22, 2: PRINT "The reassembled press-kit text would print here."
LOCATE 23, 2: PRINT "For the real thing, run the generated .COM in DOSBox."
SLEEP
END
