/* Cryptomonopoly — board definition (crypto-flavoured, original, no third-party assets). */
(function (global) {
  "use strict";

  // Tile geometry: a square RING of a 7x7 grid => exactly 24 perimeter cells.
  // Rows/cols are 0..6. Positions are enumerated clockwise starting at the
  // bottom-left corner, so the geometric corners sit at indices 0,6,12,18.
  function buildPositions() {
    const pos = [];
    // bottom edge (row 6): col 0..6
    for (let c = 0; c <= 6; c++) pos.push([6, c]);
    // right edge (col 6): row 5..0
    for (let r = 5; r >= 0; r--) pos.push([r, 6]);
    // top edge (row 0): col 5..0
    for (let c = 5; c >= 0; c--) pos.push([0, c]);
    // left edge (col 0): row 1..5
    for (let r = 1; r <= 5; r++) pos.push([r, 0]);
    return pos;
  }

  const POSITIONS = buildPositions(); // POSITIONS[index] = [row, col]

  // rent: [level0..level4]
  const T = {
    GO: "GO", PROP: "PROP", EXCH: "EXCH", TAX: "TAX",
    AIRDROP: "AIRDROP", EVENT: "EVENT", POT: "POT", JAIL: "JAIL", RUG: "RUG",
  };

  // Board array. Group letters only tag tiles so we can colour side sections.
  const TILES = [
    { i: 0,  type: T.GO,   name: "GO",            sym: "◉",          group: null },
    { i: 1,  type: T.PROP, name: "Dogecoin",      sym: "DOGE", group: "A", color: "#c2a633", price: 60,  rent: [6, 18, 54, 160, 250], up: 30 },
    { i: 2,  type: T.TAX,  name: "Gas Fee",       sym: "GAS",        group: null },
    { i: 3,  type: T.PROP, name: "Litecoin",      sym: "LTC",  group: "A", color: "#a6a9aa", price: 60,  rent: [6, 18, 54, 160, 250], up: 30 },
    { i: 4,  type: T.PROP, name: "Bitcoin",       sym: "BTC",  group: "B", color: "#f7931a", price: 80,  rent: [8, 24, 72, 200, 320], up: 40 },
    { i: 5,  type: T.PROP, name: "Ethereum",      sym: "ETH",  group: "B", color: "#627eea", price: 100, rent: [10, 30, 90, 260, 400], up: 50 },
    { i: 6,  type: T.POT,  name: "Free Mint",     sym: "POT",        group: null }, // collects the pot
    { i: 7,  type: T.PROP, name: "Solana",        sym: "SOL",  group: "C", color: "#14f195", price: 120, rent: [12, 36, 108, 300, 450], up: 60 },
    { i: 8,  type: T.PROP, name: "Cardano",       sym: "ADA",  group: "C", color: "#0033ad", price: 120, rent: [12, 36, 108, 300, 450], up: 60 },
    { i: 9,  type: T.EXCH, name: "Uniswap",       sym: "UNI·DEX", group: "X", color: "#ff007a", price: 150 },
    { i: 10, type: T.AIRDROP, name: "Airdrop",    sym: "🪂",        group: null },
    { i: 11, type: T.PROP, name: "Polkadot",      sym: "DOT",  group: "D", color: "#e6007a", price: 140, rent: [14, 42, 126, 350, 560], up: 70 },
    { i: 12, type: T.JAIL, name: "Rugged (Jail)", sym: "⛓",        group: null },
    { i: 13, type: T.PROP, name: "Avalanche",     sym: "AVAX", group: "D", color: "#e84142", price: 160, rent: [16, 48, 144, 400, 640], up: 80 },
    { i: 14, type: T.PROP, name: "Chainlink",     sym: "LINK", group: "E", color: "#2a5ada", price: 180, rent: [18, 54, 162, 450, 720], up: 90 },
    { i: 15, type: T.EVENT, name: "Halving",      sym: "✳",        group: null }, // event deck
    { i: 16, type: T.PROP, name: "Polygon",       sym: "MATIC", group: "E", color: "#8247e5", price: 180, rent: [18, 54, 162, 450, 720], up: 90 },
    { i: 17, type: T.PROP, name: "Monero",        sym: "XMR",  group: "F", color: "#ff6600", price: 200, rent: [22, 66, 198, 550, 880], up: 100 },
    { i: 18, type: T.RUG,  name: "Rug Pull!",     sym: "🥾",        group: null }, // go to jail
    { i: 19, type: T.EXCH, name: "Binance",       sym: "BNB·CEX", group: "X", color: "#f0b90b", price: 200 },
    { i: 20, type: T.PROP, name: "Cosmos",        sym: "ATOM", group: "F", color: "#2e3148", price: 220, rent: [24, 72, 216, 600, 960], up: 110 },
    { i: 21, type: T.EVENT, name: "Event",        sym: "✳",        group: null },
    { i: 22, type: T.EXCH, name: "Coinbase",      sym: "COIN·CEX", group: "X", color: "#0052ff", price: 200 },
    { i: 23, type: T.PROP, name: "Near",          sym: "NEAR", group: "F", color: "#8a7bff", price: 240, rent: [26, 78, 234, 650, 1040], up: 120 },
  ];

  // Event (chance/halving) deck — effects are deterministic after draw.
  const EVENT_DECK = [
    { text: "🚀 Bull run! Collect 200 from the network pot.", kind: "cash", value: 200, fromPot: true },
    { text: "🩸 Bear market. Pay 100 network fee into the pot.", kind: "cash", value: -100, toPot: true },
    { text: "🪂 Surprise airdrop: +150.", kind: "cash", value: 150, fromPot: false },
    { text: "👮 Proof-of-authority audit. Go straight to Rugged (jail).", kind: "jail" },
    { text: "🎁 Free NFT mint. Receive 80.", kind: "cash", value: 80, fromPot: false },
    { text: "📉 Liquidation cascade. Pay 120 into the pot.", kind: "cash", value: -120, toPot: true },
    { text: "🌕 To the moon! Advance to GO.", kind: "move", target: 0 },
    { text: "📡 Validator reward. Collect 100.", kind: "cash", value: 100, fromPot: false },
  ];

  const GO_SALARY = 200;
  const POT_START = 200; // money that starts in the free-mint pot
  const JAIL_INDEX = 12;
  const START_CASH = 1500;
  const BOARD_SIZE = 24;

  const TOKENS = [
    { id: "btc",  label: "Bitcoin",   glyph: "🪙" },
    { id: "rocket", label: "Rocket",  glyph: "🚀" },
    { id: "bot",  label: "CryptoBot", glyph: "🤖" },
    { id: "whale", label: "Whale",    glyph: "🐋" },
    { id: "ape",  label: "Ape",       glyph: "🦧" },
    { id: "shark", label: "Shark",    glyph: "🦈" },
    { id: "moon", label: "Moon",      glyph: "🌙" },
    { id: "hand", label: "DiamondHand", glyph: "💎" },
  ];

  const PLAYER_COLORS = ["#f43f5e", "#22d3ee", "#a3e635", "#f59e0b", "#a78bfa", "#f472b6"];

  function tileByIndex(i) { return TILES[i % BOARD_SIZE]; }

  global.CryptoBoard = {
    TILES, POSITIONS, EVENT_DECK, TOKENS, PLAYER_COLORS,
    GO_SALARY, POT_START, JAIL_INDEX, START_CASH, BOARD_SIZE,
    type: T, tileByIndex,
  };
})(typeof window !== "undefined" ? window : globalThis);
