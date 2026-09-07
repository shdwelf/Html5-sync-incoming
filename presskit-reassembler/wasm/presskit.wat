;; ============================================================================
;; presskit.wat -- Original WebAssembly "cipher + checksum" engine
;; used by the Press Kit Reassembler (HTML5).
;;
;; The browser app reads user form variables, writes each section's plaintext
;; into this module's linear memory, and calls these exports to transform the
;; bytes exactly the way a classic 1990s DOS electronic press kit stored them:
;;
;;    kind 0 : XOR     (key)            e.g. key 0x5A  -- runtime decrypt-in-place
;;    kind 1 : ROT13   (symmetric)
;;    kind 2 : Caesar  (key = shift)    e.g. shift 7
;;    kind 3 : plain   (identity)
;;
;; A '$' (0x24) byte is the classic DOS "display string" terminator and is
;; deliberately left unencoded so a real INT 21h AH=09h runtime stops there.
;; ============================================================================
(module
  ;; 32 x 64 KB pages = 2 MB linear memory (matches the loader suite layout style)
  (memory (export "memory") 32)

  ;; --------------------------------------------------------------------------
  ;; encode(kind, key, src, len, dst) -> i32 (the encoded length, == len)
  ;; Reads len bytes at src, writes the transformed bytes at dst.
  ;; --------------------------------------------------------------------------
  (func (export "encode") (param $kind i32) (param $key i32) (param $src i32)
        (param $len i32) (param $dst i32) (result i32)
    (local $i i32) (local $b i32)
    (local.set $i (i32.const 0))
    (block $done
      (loop $loop
        (br_if $done (i32.ge_u (local.get $i) (local.get $len)))
        (local.set $b
          (i32.load8_u (i32.add (local.get $src) (local.get $i))))
        (if (i32.ne (local.get $b) (i32.const 0x24))
          (then
            ;; select transform by kind
            (if (i32.eq (local.get $kind) (i32.const 0))
              (then
                ;; XOR
                (local.set $b (i32.xor (local.get $b) (local.get $key)))))
            (if (i32.eq (local.get $kind) (i32.const 2))
              (then
                ;; Caesar: rotate A-Z and a-z by key, wrap within alphabet
                (local.set $b (call $caesar_char (local.get $b) (local.get $key)))))
            (if (i32.eq (local.get $kind) (i32.const 1))
              (then
                ;; ROT13 == Caesar shift 13 over letters only
                (local.set $b (call $caesar_char (local.get $b) (i32.const 13))))))
        )
        (i32.store8 (i32.add (local.get $dst) (local.get $i)) (local.get $b))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)
      )
    )
    (local.get $len)
  )

  ;; --------------------------------------------------------------------------
  ;; Caesar over a single letter byte b with shift key (A-Z / a-z wrap).
  ;; --------------------------------------------------------------------------
  (func $caesar_char (param $b i32) (param $shift i32) (result i32)
    (local $r i32)
    (local.set $r (local.get $b))
    ;; uppercase A-Z (65..90)
    (if (i32.and (i32.ge_u (local.get $b) (i32.const 65))
                 (i32.le_u (local.get $b) (i32.const 90)))
      (then
        (local.set $r
          (i32.add (i32.const 65)
            (i32.rem_u
              (i32.add (i32.sub (local.get $b) (i32.const 65)) (local.get $shift))
              (i32.const 26))))))
    ;; lowercase a-z (97..122)
    (if (i32.and (i32.ge_u (local.get $b) (i32.const 97))
                 (i32.le_u (local.get $b) (i32.const 122)))
      (then
        (local.set $r
          (i32.add (i32.const 97)
            (i32.rem_u
              (i32.add (i32.sub (local.get $b) (i32.const 97)) (local.get $shift))
              (i32.const 26))))))
    (local.get $r)
  )

  ;; --------------------------------------------------------------------------
  ;; crc16(ptr, len) -> i32  (CCITT-16 style checksum used for the DOS header)
  ;; --------------------------------------------------------------------------
  (func (export "crc16") (param $ptr i32) (param $len i32) (result i32)
    (local $i i32) (local $crc i32) (local $b i32) (local $t i32)
    (local.set $crc (i32.const 0xFFFF))
    (local.set $i (i32.const 0))
    (block $done
      (loop $loop
        (br_if $done (i32.ge_u (local.get $i) (local.get $len)))
        (local.set $b
          (i32.load8_u (i32.add (local.get $ptr) (local.get $i))))
        (local.set $crc (i32.xor (local.get $crc) (local.get $b)))
        (local.set $t (i32.const 0))
        (block $bitdone
          (loop $bitloop
            (br_if $bitdone (i32.ge_u (local.get $t) (i32.const 8)))
            (if (i32.and (local.get $crc) (i32.const 1))
              (then
                (local.set $crc (i32.xor (i32.shr_u (local.get $crc) (i32.const 1))
                                          (i32.const 0xA001))))
              (else
                (local.set $crc (i32.shr_u (local.get $crc) (i32.const 1)))))
            (local.set $t (i32.add (local.get $t) (i32.const 1)))
            (br $bitloop)
          )
        )
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)
      )
    )
    (local.get $crc)
  )
)
