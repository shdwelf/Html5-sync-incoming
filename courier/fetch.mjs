// Wormhole.app room downloader — reverse-engineered from the Next.js client
// (see courier/js*) and webtorrent/wormhole-crypto (RFC 8188 / ECE).
//
//   room   : path component of https://wormhole.app/<roomId>#<key>
//   key    : base64url 16-byte secret from the URL fragment
//   salt   : GET /api/room/<id>/salt
//   auth   : HKDF-SHA256(key, salt, "authentication") -> "Bearer sync-v1 <b64>"
//   torrent: GET /api/room/<id> -> encryptedTorrentFile (16-byte IV + AES-GCM,
//            metaKey = HKDF key with info "metadata")
//   data   : POST /api/room/<id>/b2/auth-download -> {downloadUrl, authorizationToken}
//            GET <downloadUrl>/file/socket-dev-prod/<roomId>/<piece>?Authorization=<tok>
//            The pieces concatenate into ONE aes128gcm ECE stream per file
//            (torrent file lengths are the ENCRYPTED sizes).
//
// Usage: node fetch.mjs <roomId> <key> <outdir>

import { webcrypto } from 'node:crypto'
import { createWriteStream } from 'node:fs'
import fs from 'node:fs'

const crypto = webcrypto
const enc = new TextEncoder()
const [roomId, keyB64Url, outDir] = process.argv.slice(2)
if (!roomId || !keyB64Url || !outDir) {
  console.error('usage: fetch.mjs <roomId> <key> <outdir>')
  process.exit(2)
}
const ROOM = encodeURIComponent(roomId)

function b64urlToBytes (s) {
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((s.length + 3) % 4)
  return new Uint8Array(Buffer.from(b64, 'base64'))
}

async function api (path, opts = {}) {
  const res = await fetch('https://wormhole.app' + path, opts)
  const text = await res.text()
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}: ${text.slice(0, 300)}`)
  try { return JSON.parse(text) } catch { return text }
}

// ---------------- keychain (mirrors wormhole-crypto/lib/keychain.js) -------
const key = b64urlToBytes(keyB64Url)
if (key.length !== 16) throw new Error('fragment key must be 16 bytes, got ' + key.length)

const saltResp = await api(`/api/room/${ROOM}/salt`)
console.log('salt response:', JSON.stringify(saltResp))
const salt = b64urlToBytes(saltResp.salt)

const mainKey = await crypto.subtle.importKey('raw', key, 'HKDF', false, ['deriveBits', 'deriveKey'])
const hkdfBits = (s, info, bits) =>
  crypto.subtle.deriveBits({ name: 'HKDF', hash: 'SHA-256', salt: s, info: enc.encode(info) }, mainKey, bits)
const authToken = new Uint8Array(await hkdfBits(salt, 'authentication', 128))
const authHeader = 'Bearer sync-v1 ' + Buffer.from(authToken).toString('base64')
const metaKey = await crypto.subtle.deriveKey(
  { name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode('metadata') },
  mainKey, { name: 'AES-GCM', length: 128 }, false, ['decrypt'])

// ---------------- room info -------------------------------------------------
const room = await api(`/api/room/${ROOM}`, { headers: { Authorization: authHeader } })
console.log('room:', JSON.stringify({
  id: room.id, cloudState: room.cloudState, lifetime: room.lifetime,
  maxDownloads: room.maxDownloads, remainingDownloads: room.remainingDownloads,
  expires: room.expiresAtTimestampMs && new Date(room.expiresAtTimestampMs).toISOString(),
  multiFile: room.multiFile, etfLen: (room.encryptedTorrentFile || '').length
}))
if (!room.encryptedTorrentFile) throw new Error('no encryptedTorrentFile in room response')

const etf = Buffer.from(room.encryptedTorrentFile, 'base64')
const torrentBytes = new Uint8Array(await crypto.subtle.decrypt(
  { name: 'AES-GCM', iv: etf.subarray(0, 16), tagLength: 128 }, metaKey, etf.subarray(16)))
fs.writeFileSync(outDir + '/recovered.torrent', torrentBytes)
console.log('torrent decrypted:', torrentBytes.length, 'bytes')

// ---------------- bencode parse ---------------------------------------------
function parseBencode (buf) {
  let pos = 0
  const dec = () => {
    const c = buf[pos]
    if (c === 0x69) {
      const end = buf.indexOf(0x65, pos)
      const n = Number(buf.toString('latin1', pos + 1, end))
      pos = end + 1
      return n
    }
    if (c === 0x6c || c === 0x64) {
      pos++
      const isDict = c === 0x64
      const out = isDict ? {} : []
      for (;;) {
        if (buf[pos] === 0x65) { pos++; break }
        if (isDict) { const k = dec().toString('latin1'); out[k] = dec() } else out.push(dec())
      }
      return out
    }
    const colon = buf.indexOf(0x3a, pos)
    const len = Number(buf.toString('latin1', pos, colon))
    const start = colon + 1
    pos = start + len
    return buf.subarray(start, start + len)
  }
  return dec()
}

const td = parseBencode(Buffer.from(torrentBytes))
const pieceLength = td.info['piece length']
const pieceCount = td.info.pieces.length / 20
const files = td.info.files
  ? td.info.files.map(f => ({ path: f.path.map(p => p.toString('utf8')).join('/'), length: f.length }))
  : [{ path: td.info.name.toString('utf8'), length: td.info.length }]
const totalEncrypted = files.reduce((a, f) => a + f.length, 0)
console.log('pieceLength:', pieceLength, 'pieces:', pieceCount, 'total ENCRYPTED bytes:', totalEncrypted)
for (const f of files) console.log(' file (encrypted length):', f.path, f.length)
fs.writeFileSync(outDir + '/files.json', JSON.stringify(files, null, 2))

// ---------------- B2 auth ----------------------------------------------------
const b2 = await api(`/api/room/${ROOM}/b2/auth-download`, {
  method: 'POST', headers: { Authorization: authHeader }
})
console.log('b2 downloadUrl:', b2.downloadUrl)
if (!b2.downloadUrl || !b2.authorizationToken) throw new Error('b2 auth failed: ' + JSON.stringify(b2))

async function fetchPiece (p) {
  const path = [roomId, p].map(encodeURIComponent).join('/')
  const url = `${b2.downloadUrl}/file/socket-dev-prod/${path}?Authorization=${b2.authorizationToken}`
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error('HTTP ' + res.status + ': ' + (await res.text()).slice(0, 200))
      return new Uint8Array(await res.arrayBuffer())
    } catch (e) {
      console.warn(`piece ${p} attempt ${attempt + 1} failed: ${e.message}`)
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)))
    }
  }
  throw new Error('piece ' + p + ' unrecoverable')
}

// ---------------- streaming ECE decrypt of the concatenated pieces ----------
// One ECE stream per file; for this room: single file -> one stream overall.
let pending = Buffer.alloc(0)
let hdr = null // {salt, rs, cek, nonceBase}
let seq = 0
let fileIdx = 0
let fileWritten = 0
let encConsumed = 0
let writer = null
let plainExpected = null // per current file, once header known

function plaintextSizeOf (encSize, rs) {
  const meta = 17
  const records = encSize - 21
  return records - meta * Math.ceil(records / rs)
}

async function ensureHeader () {
  if (hdr || pending.length < 21) return
  const rs = pending.readUInt32BE(16)
  const idlen = pending[20]
  if (idlen !== 0) throw new Error('non-zero keyid unsupported')
  const eceSalt = pending.subarray(0, 16)
  pending = pending.subarray(21)
  encConsumed = 21
  const cek = await crypto.subtle.deriveKey(
    { name: 'HKDF', hash: 'SHA-256', salt: eceSalt, info: enc.encode('Content-Encoding: aes128gcm\0') },
    mainKey, { name: 'AES-GCM', length: 128 }, false, ['decrypt'])
  const nonceBase = new Uint8Array(await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: eceSalt, info: enc.encode('Content-Encoding: nonce\0') },
    mainKey, 96))
  hdr = { rs, cek, nonceBase }
  const f = files[fileIdx]
  plainExpected = plaintextSizeOf(f.length, rs)
  const safeName = f.path.replace(/\//g, '__')
  writer = createWriteStream(outDir + '/' + safeName)
  console.log(`ECE header: rs=${rs}, file=${f.path}, encrypted=${f.length}, plaintext size=${plainExpected}`)
}

async function drain () {
  for (;;) {
    if (fileIdx >= files.length) {
      if (pending.length > 0) console.warn('trailing bytes:', pending.length)
      return
    }
    if (!hdr) { await ensureHeader(); if (!hdr) return }
    const rs = hdr.rs
    const budget = files[fileIdx].length
    const remaining = budget - encConsumed // encrypted bytes left in this file's stream
    if (pending.length === 0) return
    // final record of the file may be shorter than rs; piece boundaries do NOT
    // align with file boundaries, so use the per-file encrypted budget to frame it
    const recLen = Math.min(rs, remaining)
    if (recLen < 17) throw new Error('record too short: ' + recLen)
    if (pending.length < recLen) return // wait for more bytes
    const rec = pending.subarray(0, recLen)
    pending = pending.subarray(recLen)
    encConsumed += recLen
    const nonce = hdr.nonceBase.slice()
    const dv = new DataView(nonce.buffer)
    dv.setUint32(8, (dv.getUint32(8) ^ seq) >>> 0)
    let pt
    try {
      pt = new Uint8Array(await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: nonce, tagLength: 128 }, hdr.cek, rec))
    } catch (e) {
      throw new Error(`GCM fail file=${fileIdx} seq=${seq} recLen=${recLen} remaining=${remaining}: ${e}`)
    }
    let end = pt.length - 1
    while (end >= 0 && pt[end] === 0) end--
    if (end < 0) throw new Error('no delimiter')
    const delim = pt[end]
    const isFinal = encConsumed >= budget
    const expectDelim = isFinal ? 2 : 1
    if (delim !== expectDelim) throw new Error(`bad delimiter ${delim} (expected ${expectDelim}) seq ${seq}`)
    const data = Buffer.from(pt.subarray(0, end))
    writer.write(data)
    fileWritten += data.length
    seq++
    if (isFinal) {
      await new Promise(r => writer.end(r))
      console.log(`file complete: ${files[fileIdx].path} (${fileWritten} bytes, expected ${plainExpected})`)
      if (fileWritten !== plainExpected) throw new Error('size mismatch')
      fileIdx++; fileWritten = 0; writer = null
      hdr = null; seq = 0; plainExpected = null; encConsumed = 0
    }
  }
}

const t0 = Date.now()
let encDone = 0
for (let p = 0; p < pieceCount; p++) {
  const buf = await fetchPiece(p)
  encDone += buf.length
  pending = Buffer.concat([pending, Buffer.from(buf)])
  await drain()
  if (p % 2 === 0 || p === pieceCount - 1) {
    console.log(`piece ${p + 1}/${pieceCount}  encrypted ${encDone}/${totalEncrypted}  ${Math.round((Date.now() - t0) / 1000)}s`)
  }
}
await drain()
if (fileIdx < files.length) throw new Error(`unfinished: stopped at file ${fileIdx}`)
console.log('ALL FILES WRITTEN')
