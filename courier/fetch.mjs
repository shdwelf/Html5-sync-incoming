// Wormhole.app room downloader — reverse-engineered from the Next.js client
// (see courier/js*) and webtorrent/wormhole-crypto (RFC 8188 / ECE).
//
//   room  : path component of https://wormhole.app/<roomId>#<key>
//   key   : base64url 16-byte secret from the URL fragment
//   salt  : GET /api/room/<id>/salt
//   auth  : HKDF-SHA256(key, salt, "authentication") -> "Bearer sync-v1 <b64>"
//   torrent: GET /api/room/<id> -> encryptedTorrentFile (16-byte IV + AES-GCM,
//            metaKey = HKDF key with info "metadata")
//   pieces : POST /api/room/<id>/b2/auth-download -> {downloadUrl, authorizationToken}
//            GET <downloadUrl>/file/socket-dev-prod/<roomId>/<piece>?Authorization=<tok>
//            each piece is an independent aes128gcm ECE stream under the main key
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

// ---------------- keychain (mirrors wormhole-crypto/lib/keychain.js) -------
const key = b64urlToBytes(keyB64Url)
if (key.length !== 16) throw new Error('fragment key must be 16 bytes, got ' + key.length)

async function api (path, opts = {}) {
  const res = await fetch('https://wormhole.app' + path, opts)
  const text = await res.text()
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}: ${text.slice(0, 300)}`)
  try { return JSON.parse(text) } catch { return text }
}

const saltResp = await api(`/api/room/${ROOM}/salt`, { headers: { accept: 'application/json' } })
console.log('salt response:', JSON.stringify(saltResp))
const salt = b64urlToBytes(saltResp.salt)

const mainKey = await crypto.subtle.importKey('raw', key, 'HKDF', false, ['deriveBits', 'deriveKey'])
const hkdfBits = (salt, info, bits) =>
  crypto.subtle.deriveBits({ name: 'HKDF', hash: 'SHA-256', salt, info: enc.encode(info) }, mainKey, bits)
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
if (room.cloudState !== 'uploaded') console.warn('WARNING: cloudState is', room.cloudState)

// decrypt torrent metadata: 16-byte IV + AES-GCM ciphertext
const etf = Buffer.from(room.encryptedTorrentFile, 'base64')
const iv = etf.subarray(0, 16)
const torrentBytes = new Uint8Array(await crypto.subtle.decrypt(
  { name: 'AES-GCM', iv, tagLength: 128 }, metaKey, etf.subarray(16)))
fs.writeFileSync(outDir + '/recovered.torrent', torrentBytes)
console.log('torrent decrypted:', torrentBytes.length, 'bytes')

// ---------------- bencode parse ---------------------------------------------
function parseBencode (buf) {
  let pos = 0
  const dec = () => {
    const c = buf[pos]
    if (c === 0x69) { // i<int>e
      const end = buf.indexOf(0x65, pos)
      const n = Number(buf.toString('latin1', pos + 1, end))
      pos = end + 1
      return n
    }
    if (c === 0x6c || c === 0x64) { // list / dict
      pos++
      const isDict = c === 0x64
      const out = isDict ? {} : []
      for (;;) {
        if (buf[pos] === 0x65) { pos++; break }
        if (isDict) {
          const k = dec().toString('latin1')
          out[k] = dec()
        } else out.push(dec())
      }
      return out
    }
    // <len>:<bytes>
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
const piecesHash = td.info.pieces // 20 bytes per piece
const pieceCount = piecesHash.length / 20
const isMulti = !!td.info.files
const files = isMulti
  ? td.info.files.map(f => ({ path: f.path.map(p => p.toString('utf8')).join('/'), length: f.length }))
  : [{ path: td.info.name.toString('utf8'), length: td.info.length }]
const total = files.reduce((a, f) => a + f.length, 0)
console.log('pieceLength:', pieceLength, 'pieces:', pieceCount, 'total plaintext bytes:', total)
for (const f of files) console.log(' file:', f.path, f.length)
fs.writeFileSync(outDir + '/files.json', JSON.stringify(files, null, 2))

// ---------------- B2 auth ----------------------------------------------------
const b2 = await api(`/api/room/${ROOM}/b2/auth-download`, {
  method: 'POST', headers: { Authorization: authHeader }
})
console.log('b2 downloadUrl:', b2.downloadUrl)
if (!b2.downloadUrl || !b2.authorizationToken) throw new Error('b2 auth failed: ' + JSON.stringify(b2))

// ---------------- ECE (RFC 8188) record decrypt ------------------------------
async function decryptPiece (bytes) {
  if (bytes.length < 21) throw new Error('piece too short')
  const rs = (bytes[16] << 24 | bytes[17] << 16 | bytes[18] << 8 | bytes[19]) >>> 0
  const idlen = bytes[20]
  if (idlen !== 0) throw new Error('non-zero keyid unsupported')
  const eceSalt = bytes.subarray(0, 16)
  const cek = await crypto.subtle.deriveKey(
    { name: 'HKDF', hash: 'SHA-256', salt: eceSalt, info: enc.encode('Content-Encoding: aes128gcm\0') },
    mainKey, { name: 'AES-GCM', length: 128 }, false, ['decrypt'])
  const nonceBase = new Uint8Array(await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: eceSalt, info: enc.encode('Content-Encoding: nonce\0') },
    mainKey, 96))
  const out = []
  let off = 21
  let seq = 0
  while (off < bytes.length) {
    const rec = bytes.subarray(off, Math.min(off + rs, bytes.length))
    off += rs
    const isLast = off >= bytes.length
    const nonce = nonceBase.slice()
    const dv = new DataView(nonce.buffer)
    dv.setUint32(8, (dv.getUint32(8) ^ seq) >>> 0)
    const pt = new Uint8Array(await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: nonce, tagLength: 128 }, cek, rec))
    // strip padding: last non-zero byte is delimiter (2 = final record)
    let end = pt.length - 1
    while (end >= 0 && pt[end] === 0) end--
    if (end < 0) throw new Error('no delimiter')
    if (pt[end] !== (isLast ? 2 : 1)) throw new Error(`bad delimiter ${pt[end]} seq ${seq} isLast ${isLast}`)
    out.push(pt.subarray(0, end))
    seq++
  }
  return Buffer.concat(out)
}

// ---------------- stream all pieces into per-file writers ---------------------
const writers = files.map(f => ({ ...f, written: 0, ws: createWriteStream(outDir + '/' + f.path.replace(/\//g, '__')) }))
let fileIdx = 0
let inFileOff = 0
const t0 = Date.now()
for (let p = 0; p < pieceCount; p++) {
  const path = [roomId, p].map(encodeURIComponent).join('/')
  const url = `${b2.downloadUrl}/file/socket-dev-prod/${path}?Authorization=${b2.authorizationToken}`
  let buf = null
  for (let attempt = 0; attempt < 6 && buf === null; attempt++) {
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error('HTTP ' + res.status)
      buf = new Uint8Array(await res.arrayBuffer())
    } catch (e) {
      console.warn(`piece ${p} attempt ${attempt + 1} failed: ${e.message}`)
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)))
    }
  }
  if (buf === null) throw new Error('piece ' + p + ' unrecoverable')
  const plain = await decryptPiece(buf)
  let need = plain.length
  let src = 0
  while (need > 0) {
    const w = writers[fileIdx]
    const space = w.length - inFileOff
    const take = Math.min(space, need)
    if (take > 0) w.ws.write(Buffer.from(plain.subarray(src, src + take)))
    src += take; need -= take; inFileOff += take; w.written += take
    if (inFileOff >= w.length) { w.ws.end(); fileIdx++; inFileOff = 0 }
  }
  if (p % 25 === 0 || p === pieceCount - 1) {
    const done = writers.reduce((a, w) => a + w.written, 0)
    console.log(`piece ${p + 1}/${pieceCount}  ${done}/${total} bytes  ${Math.round((Date.now() - t0) / 1000)}s`)
  }
}
for (const w of writers) await new Promise(r => w.ws.close(r))
console.log('ALL FILES WRITTEN')
