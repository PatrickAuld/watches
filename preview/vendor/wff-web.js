// wff-web 0.1.1 (https://www.npmjs.com/package/wff-web), vendored with two patches:
// 1. buildDataSources also supplies SECONDS_SINCE_EPOCH, MINUTES_SINCE_EPOCH,
//    MILLISECOND, SECOND_MILLISECOND and MINUTE_SECOND, which Radar and Radial
//    Moire use for motion.
// 2. renderWatchFaceFrame draws one double-buffered frame at a given clock time
//    and animation elapsed time, so the preview pages drive their own animation
//    loop (start from any time, share a frame budget across many canvases, no
//    half-drawn frames).
// 3. Expressions are tokenized and parsed once and cached by their text, and
//    renderWatchFaceFrame parses each face's XML once and reuses it, undoing
//    the attribute writes each frame makes (transforms write into the DOM). Faces
//    with hundreds of long expressions, like Thread Portrait, otherwise spend
//    most of each frame re-parsing text that never changes. Groups whose
//    alpha is 0 are skipped (they draw nothing), and masking layers are pooled
//    instead of allocated twice a frame.
// 4. Decoded images are cached per face (per asset map), not globally by
//    resource name: Book of Hours and Book of Hours II share 66 names, and the
//    gallery showed one face's images in the other.
// 5. Condition follows the WFF spec: an Expression's text is its expression,
//    and a Compare's expression attribute names one of those Expressions.
// Drop this file once wff-web publishes these.
// src/color.ts
function parseColor(value) {
  if (value == null) return "#000000";
  if (value.length === 9 && value.startsWith("#")) {
    const a = parseInt(value.slice(1, 3), 16);
    const r = parseInt(value.slice(3, 5), 16);
    const g = parseInt(value.slice(5, 7), 16);
    const b = parseInt(value.slice(7, 9), 16);
    const alpha = Number((a / 255).toFixed(3));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return value;
}

// src/styles.ts
function applyFill(ctx, el) {
  const fillEl = el.querySelector(":scope > Fill");
  if (!fillEl) return;
  const gradient = createGradient(ctx, fillEl);
  if (gradient) {
    ctx.fillStyle = gradient;
  } else {
    ctx.fillStyle = parseColor(fillEl.getAttribute("color"));
  }
  ctx.fill();
}
function applyStroke(ctx, el) {
  const strokeEl = el.querySelector(":scope > Stroke");
  if (!strokeEl) return;
  ctx.strokeStyle = parseColor(strokeEl.getAttribute("color"));
  ctx.lineWidth = parseFloat(strokeEl.getAttribute("thickness") ?? "1");
  const cap = strokeEl.getAttribute("cap");
  if (cap === "ROUND") ctx.lineCap = "round";
  else if (cap === "SQUARE") ctx.lineCap = "square";
  else ctx.lineCap = "butt";
  const dashAttr = strokeEl.getAttribute("dashIntervals");
  if (dashAttr) {
    ctx.setLineDash(dashAttr.split(/\s+/).map(Number));
  } else {
    ctx.setLineDash([]);
  }
  ctx.lineDashOffset = parseFloat(
    strokeEl.getAttribute("dashPhase") ?? "0"
  );
  ctx.stroke();
}
function createGradient(ctx, fillEl) {
  const linear = fillEl.querySelector(":scope > LinearGradient");
  if (linear) {
    return createLinearGradient(ctx, linear);
  }
  const radial = fillEl.querySelector(":scope > RadialGradient");
  if (radial) {
    return createRadialGradient(ctx, radial);
  }
  const sweep = fillEl.querySelector(":scope > SweepGradient");
  if (sweep) {
    return createSweepGradient(ctx, sweep);
  }
  return null;
}
function addColorStops(gradient, el, positionScale = 1) {
  const colorsAttr = el.getAttribute("colors") ?? "";
  const positionsAttr = el.getAttribute("positions") ?? "";
  const colors = colorsAttr.split(/\s+/).filter(Boolean);
  const positions = positionsAttr.split(/\s+/).filter(Boolean).map(Number);
  const clampedScale = clampStop(positionScale);
  let lastStop = 0;
  for (let i = 0; i < colors.length; i++) {
    const basePos = i < positions.length ? positions[i] : colors.length <= 1 ? 0 : i / (colors.length - 1);
    const pos = clampStop(basePos * clampedScale);
    lastStop = pos;
    gradient.addColorStop(pos, parseColor(colors[i]));
  }
  if (colors.length > 0 && clampedScale < 1 && lastStop < 1) {
    gradient.addColorStop(1, parseColor(colors.at(-1)));
  }
  return gradient;
}
function createLinearGradient(ctx, el) {
  const x0 = parseFloat(el.getAttribute("startX") ?? "0");
  const y0 = parseFloat(el.getAttribute("startY") ?? "0");
  const x1 = parseFloat(el.getAttribute("endX") ?? "0");
  const y1 = parseFloat(el.getAttribute("endY") ?? "0");
  return addColorStops(ctx.createLinearGradient(x0, y0, x1, y1), el);
}
function createRadialGradient(ctx, el) {
  const cx = parseFloat(el.getAttribute("centerX") ?? "0");
  const cy = parseFloat(el.getAttribute("centerY") ?? "0");
  const r = parseFloat(el.getAttribute("radius") ?? "0");
  return addColorStops(ctx.createRadialGradient(cx, cy, 0, cx, cy, r), el);
}
function createSweepGradient(ctx, el) {
  const cx = parseFloat(el.getAttribute("centerX") ?? "0");
  const cy = parseFloat(el.getAttribute("centerY") ?? "0");
  const startAngle = parseFloat(el.getAttribute("startAngle") ?? "0");
  const endAngle = parseFloat(el.getAttribute("endAngle") ?? "360");
  const startRad = (startAngle - 90) * Math.PI / 180;
  const sweepFraction = getSweepFraction(startAngle, endAngle);
  return addColorStops(
    ctx.createConicGradient(startRad, cx, cy),
    el,
    sweepFraction
  );
}
function getSweepFraction(startAngle, endAngle) {
  const rawSweep = endAngle - startAngle;
  if (!Number.isFinite(rawSweep) || Math.abs(rawSweep) >= 360) {
    return 1;
  }
  const normalizedSweep = (rawSweep % 360 + 360) % 360;
  return normalizedSweep === 0 ? 1 : normalizedSweep / 360;
}
function clampStop(value) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(1, Math.max(0, value));
}

// Attribute writes made while rendering a frame are journaled on the document
// and undone afterwards, so a parsed face can be reused frame after frame.
function setAttr(el, name, value) {
  const journal = el.ownerDocument.__journal;
  if (journal) journal.push(el, name, el.getAttribute(name));
  el.setAttribute(name, value);
}
function undoJournal(doc) {
  const journal = doc.__journal;
  doc.__journal = null;
  for (let i = journal.length - 3; i >= 0; i -= 3) {
    const value = journal[i + 2];
    if (value === null) journal[i].removeAttribute(journal[i + 1]);
    else journal[i].setAttribute(journal[i + 1], value);
  }
}

// src/variants.ts
function applyVariants(el, ambient) {
  for (const child of el.children) {
    if (child.tagName === "Variant") {
      const mode = child.getAttribute("mode");
      if (mode === "AMBIENT" && ambient) {
        const target = child.getAttribute("target");
        const value = child.getAttribute("value");
        if (target !== null && value !== null) {
          setAttr(el, target, value);
        }
      }
    }
  }
}

// src/masking.ts
var BLEND_MODE_MAP = {
  SRC_OVER: "source-over",
  MULTIPLY: "multiply",
  SCREEN: "screen",
  OVERLAY: "overlay",
  DARKEN: "darken",
  LIGHTEN: "lighten"
};
function applyBlendMode(ctx, el) {
  const mode = el.getAttribute("blendMode");
  if (mode && BLEND_MODE_MAP[mode]) {
    ctx.globalCompositeOperation = BLEND_MODE_MAP[mode];
  }
}
function hasMasking(el) {
  for (const child of el.children) {
    const rm = child.getAttribute("renderMode");
    if (rm === "SOURCE" || rm === "MASK") return true;
  }
  return false;
}
// Masking layers are pooled: allocating 450x450 canvases twice a frame was a
// large share of frame time for masked faces.
const layerPool = [];
function acquireLayer(width, height) {
  const i = layerPool.findIndex(c => c.width === width && c.height === height);
  const offscreen = i >= 0 ? layerPool.splice(i, 1)[0] : new OffscreenCanvas(width, height);
  const offCtx = offscreen.getContext("2d");
  offCtx.setTransform(1, 0, 0, 1, 0, 0);
  offCtx.globalAlpha = 1;
  offCtx.globalCompositeOperation = "source-over";
  offCtx.clearRect(0, 0, width, height);
  return offscreen;
}
async function renderWithMasking(ctx, el, width, height, renderChild, renderCtx) {
  const offscreen = acquireLayer(width, height);
  try {
    await renderMaskedLayer(ctx, el, offscreen, renderChild, renderCtx);
  } finally {
    if (layerPool.length < 16) layerPool.push(offscreen);
  }
}
async function renderMaskedLayer(ctx, el, offscreen, renderChild, renderCtx) {
  const offCtx = offscreen.getContext("2d");
  for (const child of el.children) {
    const rm = child.getAttribute("renderMode");
    if (rm === "SOURCE" || !rm) {
      if (child.tagName !== "Variant") {
        await renderChild(
          offCtx,
          child,
          renderCtx
        );
      }
    }
  }
  for (const child of el.children) {
    const rm = child.getAttribute("renderMode");
    if (rm === "MASK") {
      offCtx.globalCompositeOperation = "destination-in";
      await renderChild(
        offCtx,
        child,
        renderCtx
      );
      offCtx.globalCompositeOperation = "source-over";
    }
  }
  for (const child of el.children) {
    const rm = child.getAttribute("renderMode");
    if (rm === "ALL") {
      await renderChild(
        offCtx,
        child,
        renderCtx
      );
    }
  }
  ctx.drawImage(offscreen, 0, 0);
}

// src/expressions.ts
function tokenize(input) {
  const tokens = [];
  let i = 0;
  while (i < input.length) {
    if (/\s/.test(input[i])) {
      i++;
      continue;
    }
    if (input[i] === "[") {
      const end = input.indexOf("]", i);
      if (end === -1) throw new Error(`Unterminated source reference at ${i}`);
      tokens.push({ type: "source", value: input.slice(i + 1, end) });
      i = end + 1;
      continue;
    }
    if (input[i] === '"' || input[i] === "'") {
      const quote = input[i];
      let str = "";
      i++;
      while (i < input.length && input[i] !== quote) {
        if (input[i] === "\\" && i + 1 < input.length) {
          i++;
          str += input[i];
        } else {
          str += input[i];
        }
        i++;
      }
      i++;
      tokens.push({ type: "string", value: str });
      continue;
    }
    if (/[0-9]/.test(input[i]) || input[i] === "." && /[0-9]/.test(input[i + 1] ?? "")) {
      let num = "";
      while (i < input.length && /[0-9.]/.test(input[i])) {
        num += input[i];
        i++;
      }
      tokens.push({ type: "number", value: parseFloat(num) });
      continue;
    }
    const two = input.slice(i, i + 2);
    if (two === "==" || two === "!=" || two === "<=" || two === ">=" || two === "&&" || two === "||") {
      tokens.push({ type: two, value: two });
      i += 2;
      continue;
    }
    const ch = input[i];
    if ("+-*/%<>!~|&?:(),".includes(ch)) {
      tokens.push({ type: ch, value: ch });
      i++;
      continue;
    }
    if (/[a-zA-Z_]/.test(input[i])) {
      let ident = "";
      while (i < input.length && /[a-zA-Z0-9_]/.test(input[i])) {
        ident += input[i];
        i++;
      }
      tokens.push({ type: "ident", value: ident });
      continue;
    }
    throw new Error(`Unexpected character '${input[i]}' at position ${i}`);
  }
  return tokens;
}
var Parser = class {
  tokens;
  pos;
  constructor(tokens) {
    this.tokens = tokens;
    this.pos = 0;
  }
  peek() {
    return this.tokens[this.pos];
  }
  consume() {
    const tok = this.tokens[this.pos];
    if (!tok) throw new Error("Unexpected end of expression");
    this.pos++;
    return tok;
  }
  expect(type) {
    const tok = this.consume();
    if (tok.type !== type) {
      throw new Error(`Expected token '${type}', got '${tok.type}'`);
    }
    return tok;
  }
  parse() {
    const node = this.parseTernary();
    if (this.pos < this.tokens.length) {
      throw new Error(`Unexpected token '${this.tokens[this.pos].value}' at position ${this.pos}`);
    }
    return node;
  }
  // Ternary: condition ? consequent : alternate
  parseTernary() {
    const condition = this.parseOr();
    if (this.peek()?.type === "?") {
      this.consume();
      const consequent = this.parseTernary();
      this.expect(":");
      const alternate = this.parseTernary();
      return { type: "ternary", condition, consequent, alternate };
    }
    return condition;
  }
  // Logical OR
  parseOr() {
    let left = this.parseAnd();
    while (this.peek()?.type === "||") {
      const op = this.consume().type;
      const right = this.parseAnd();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Logical AND
  parseAnd() {
    let left = this.parseBitwiseOr();
    while (this.peek()?.type === "&&") {
      const op = this.consume().type;
      const right = this.parseBitwiseOr();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Bitwise OR
  parseBitwiseOr() {
    let left = this.parseBitwiseAnd();
    while (this.peek()?.type === "|") {
      const op = this.consume().type;
      const right = this.parseBitwiseAnd();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Bitwise AND
  parseBitwiseAnd() {
    let left = this.parseEquality();
    while (this.peek()?.type === "&") {
      const op = this.consume().type;
      const right = this.parseEquality();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Equality: == !=
  parseEquality() {
    let left = this.parseComparison();
    while (this.peek()?.type === "==" || this.peek()?.type === "!=") {
      const op = this.consume().type;
      const right = this.parseComparison();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Comparison: < <= > >=
  parseComparison() {
    let left = this.parseAddition();
    while (this.peek()?.type === "<" || this.peek()?.type === "<=" || this.peek()?.type === ">" || this.peek()?.type === ">=") {
      const op = this.consume().type;
      const right = this.parseAddition();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Addition: + -
  parseAddition() {
    let left = this.parseMultiplication();
    while (this.peek()?.type === "+" || this.peek()?.type === "-") {
      const op = this.consume().type;
      const right = this.parseMultiplication();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Multiplication: * / %
  parseMultiplication() {
    let left = this.parseUnary();
    while (this.peek()?.type === "*" || this.peek()?.type === "/" || this.peek()?.type === "%") {
      const op = this.consume().type;
      const right = this.parseUnary();
      left = { type: "binary", op, left, right };
    }
    return left;
  }
  // Unary: ! - ~
  parseUnary() {
    const tok = this.peek();
    if (tok?.type === "!" || tok?.type === "-" || tok?.type === "~") {
      this.consume();
      const operand = this.parseUnary();
      return { type: "unary", op: tok.type, operand };
    }
    return this.parsePrimary();
  }
  // Primary: number, string, source ref, function call, parenthesized
  parsePrimary() {
    const tok = this.peek();
    if (!tok) throw new Error("Unexpected end of expression");
    if (tok.type === "number") {
      this.consume();
      return { type: "number", value: tok.value };
    }
    if (tok.type === "string") {
      this.consume();
      return { type: "string", value: tok.value };
    }
    if (tok.type === "source") {
      this.consume();
      return { type: "source", name: tok.value };
    }
    if (tok.type === "ident") {
      this.consume();
      const name = tok.value;
      if (this.peek()?.type === "(") {
        this.consume();
        const args = [];
        if (this.peek()?.type !== ")") {
          args.push(this.parseTernary());
          while (this.peek()?.type === ",") {
            this.consume();
            args.push(this.parseTernary());
          }
        }
        this.expect(")");
        return { type: "call", name, args };
      }
      return { type: "string", value: name };
    }
    if (tok.type === "(") {
      this.consume();
      const node = this.parseTernary();
      this.expect(")");
      return node;
    }
    throw new Error(`Unexpected token '${tok.value}' (${tok.type})`);
  }
};
function numArg(args, i, fname) {
  const v = args[i];
  if (typeof v !== "number") throw new Error(`${fname}: argument ${i} must be a number, got ${v}`);
  return v;
}
var BUILTINS = {
  round: (a) => Math.round(numArg(a, 0, "round")),
  floor: (a) => Math.floor(numArg(a, 0, "floor")),
  ceil: (a) => Math.ceil(numArg(a, 0, "ceil")),
  fract: (a) => {
    const x = numArg(a, 0, "fract");
    return x - Math.floor(x);
  },
  abs: (a) => Math.abs(numArg(a, 0, "abs")),
  sqrt: (a) => Math.sqrt(numArg(a, 0, "sqrt")),
  pow: (a) => Math.pow(numArg(a, 0, "pow"), numArg(a, 1, "pow")),
  sin: (a) => Math.sin(numArg(a, 0, "sin")),
  cos: (a) => Math.cos(numArg(a, 0, "cos")),
  tan: (a) => Math.tan(numArg(a, 0, "tan")),
  asin: (a) => Math.asin(numArg(a, 0, "asin")),
  acos: (a) => Math.acos(numArg(a, 0, "acos")),
  atan: (a) => Math.atan(numArg(a, 0, "atan")),
  deg: (a) => numArg(a, 0, "deg") * (180 / Math.PI),
  rad: (a) => numArg(a, 0, "rad") * (Math.PI / 180),
  clamp: (a) => {
    const x = numArg(a, 0, "clamp");
    const min = numArg(a, 1, "clamp");
    const max = numArg(a, 2, "clamp");
    return Math.min(Math.max(x, min), max);
  },
  log: (a) => Math.log(numArg(a, 0, "log")),
  log2: (a) => Math.log2(numArg(a, 0, "log2")),
  log10: (a) => Math.log10(numArg(a, 0, "log10")),
  exp: (a) => Math.exp(numArg(a, 0, "exp")),
  numberFormat: (a) => {
    const value = numArg(a, 0, "numberFormat");
    const minIntDigits = numArg(a, 1, "numberFormat");
    return String(Math.trunc(value)).padStart(minIntDigits, "0");
  },
  subText: (a) => {
    const str = String(a[0]);
    const start = numArg(a, 1, "subText");
    const end = numArg(a, 2, "subText");
    return str.slice(start, end);
  },
  textLength: (a) => String(a[0]).length,
  icuText: (a) => String(a[0])
  // return the pattern as-is
};
function evalNode(node, ctx) {
  switch (node.type) {
    case "number":
      return node.value;
    case "string":
      return node.value;
    case "source": {
      const val = ctx.sources[node.name];
      if (val === void 0) {
        return 0;
      }
      return val;
    }
    case "unary": {
      const operand = evalNode(node.operand, ctx);
      switch (node.op) {
        case "!":
          return Number(!operand);
        case "-":
          return -operand;
        case "~":
          return ~operand;
        default:
          throw new Error(`Unknown unary operator: ${node.op}`);
      }
    }
    case "binary": {
      const left = evalNode(node.left, ctx);
      const right = evalNode(node.right, ctx);
      switch (node.op) {
        case "+":
          if (typeof left === "string" || typeof right === "string") {
            return String(left) + String(right);
          }
          return left + right;
        case "-":
          return left - right;
        case "*":
          return left * right;
        case "/":
          return left / right;
        case "%":
          return left % right;
        case "==":
          return left == right ? 1 : 0;
        case "!=":
          return left != right ? 1 : 0;
        case "<":
          return left < right ? 1 : 0;
        case "<=":
          return left <= right ? 1 : 0;
        case ">":
          return left > right ? 1 : 0;
        case ">=":
          return left >= right ? 1 : 0;
        case "&&":
          return left && right ? 1 : 0;
        case "||":
          return left || right ? 1 : 0;
        case "|":
          return left | right;
        case "&":
          return left & right;
        default:
          throw new Error(`Unknown binary operator: ${node.op}`);
      }
    }
    case "ternary": {
      const cond = evalNode(node.condition, ctx);
      return cond ? evalNode(node.consequent, ctx) : evalNode(node.alternate, ctx);
    }
    case "call": {
      const fn = BUILTINS[node.name];
      if (!fn) throw new Error(`Unknown function: ${node.name}`);
      const args = node.args.map((a) => evalNode(a, ctx));
      return fn(args);
    }
  }
}
const astCache = /* @__PURE__ */ new Map();
function evaluateExpression(expr, context) {
  let ast = astCache.get(expr);
  if (!ast) {
    ast = new Parser(tokenize(expr)).parse();
    astCache.set(expr, ast);
  }
  return evalNode(ast, context);
}
function zeroPad(value) {
  return String(value).padStart(2, "0");
}
function getDayOfYear(date) {
  const start = new Date(date.getFullYear(), 0, 0);
  const diff = date.getTime() - start.getTime();
  const oneDay = 1e3 * 60 * 60 * 24;
  return Math.floor(diff / oneDay);
}
function buildDataSources(time, config, is24Hour) {
  const second = time.getSeconds();
  const minute = time.getMinutes();
  const hour0_23 = time.getHours();
  const hour0_11 = hour0_23 % 12;
  const hour1_12 = hour0_11 === 0 ? 12 : hour0_11;
  const hour1_24 = hour0_23 === 0 ? 24 : hour0_23;
  const day = time.getDate();
  const dayOfWeek = time.getDay() + 1;
  const dayOfYear = getDayOfYear(time);
  const month = time.getMonth() + 1;
  const year = time.getFullYear();
  const ampmState = hour0_23 >= 12 ? 1 : 0;
  const is24HourMode = is24Hour !== false ? 1 : 0;
  const utcTimestamp = Math.floor(time.getTime() / 1e3);
  const sources = {
    SECOND: second,
    MINUTE: minute,
    HOUR_0_23: hour0_23,
    HOUR_1_12: hour1_12,
    HOUR_0_11: hour0_11,
    HOUR_1_24: hour1_24,
    DAY: day,
    DAY_OF_WEEK: dayOfWeek,
    DAY_OF_YEAR: dayOfYear,
    MONTH: month,
    YEAR: year,
    AMPM_STATE: ampmState,
    IS_24_HOUR_MODE: is24HourMode,
    UTC_TIMESTAMP: utcTimestamp,
    // Watch-face sub-second sources missing from wff-web 0.1.1 (local patch).
    SECONDS_SINCE_EPOCH: utcTimestamp,
    MINUTES_SINCE_EPOCH: Math.floor(utcTimestamp / 60),
    MILLISECOND: time.getMilliseconds(),
    SECOND_MILLISECOND: second + time.getMilliseconds() / 1e3,
    MINUTE_SECOND: minute + (second + time.getMilliseconds() / 1e3) / 60,
    // Zero-padded string variants
    SECOND_Z: zeroPad(second),
    MINUTE_Z: zeroPad(minute),
    HOUR_0_23_Z: zeroPad(hour0_23),
    HOUR_1_12_Z: zeroPad(hour1_12),
    HOUR_0_11_Z: zeroPad(hour0_11),
    HOUR_1_24_Z: zeroPad(hour1_24),
    DAY_Z: zeroPad(day),
    MONTH_Z: zeroPad(month),
    // Digit extraction
    SECOND_TENS_DIGIT: Math.floor(second / 10),
    SECOND_UNITS_DIGIT: second % 10,
    MINUTE_TENS_DIGIT: Math.floor(minute / 10),
    MINUTE_UNITS_DIGIT: minute % 10,
    HOUR_0_23_TENS_DIGIT: Math.floor(hour0_23 / 10),
    HOUR_0_23_UNITS_DIGIT: hour0_23 % 10,
    HOUR_1_12_TENS_DIGIT: Math.floor(hour1_12 / 10),
    HOUR_1_12_UNITS_DIGIT: hour1_12 % 10,
    HOUR_0_11_TENS_DIGIT: Math.floor(hour0_11 / 10),
    HOUR_0_11_UNITS_DIGIT: hour0_11 % 10,
    HOUR_1_24_TENS_DIGIT: Math.floor(hour1_24 / 10),
    HOUR_1_24_UNITS_DIGIT: hour1_24 % 10
  };
  if (config) {
    for (const [key, value] of Object.entries(config)) {
      sources[`CONFIGURATION.${key}`] = typeof value === "boolean" ? value ? 1 : 0 : value;
    }
  }
  return { sources };
}

// src/animation.ts
function ease(t, interpolation, controls) {
  t = Math.max(0, Math.min(1, t));
  switch (interpolation) {
    case "LINEAR":
      return t;
    case "EASE_IN":
      return t * t;
    case "EASE_OUT":
      return 1 - (1 - t) * (1 - t);
    case "EASE_IN_OUT":
      return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    case "OVERSHOOT":
      return 2.70158 * t * t * t - 1.70158 * t * t;
    case "CUBIC_BEZIER": {
      if (!controls) return t;
      const parts = controls.split(",").map(Number);
      const [x1, y1, x2, y2] = parts;
      return cubicBezier(x1, y1, x2, y2, t);
    }
    default:
      return t;
  }
}
function cubicBezier(x1, y1, x2, y2, x) {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 20; i++) {
    const mid = (lo + hi) / 2;
    const bx = 3 * (1 - mid) * (1 - mid) * mid * x1 + 3 * (1 - mid) * mid * mid * x2 + mid * mid * mid;
    if (bx < x) lo = mid;
    else hi = mid;
  }
  const t = (lo + hi) / 2;
  return 3 * (1 - t) * (1 - t) * t * y1 + 3 * (1 - t) * t * t * y2 + t * t * t;
}
function applyTransforms(el, expressionCtx, elapsedMs) {
  for (const child of el.children) {
    if (child.tagName !== "Transform") continue;
    const target = child.getAttribute("target");
    if (!target) continue;
    const valueExpr = child.getAttribute("value");
    const mode = child.getAttribute("mode") ?? "TO";
    const animEl = Array.from(child.children).find(
      (c) => c.tagName === "Animation"
    );
    if (animEl) {
      const fromAttr = child.getAttribute("from");
      const toAttr = child.getAttribute("to");
      if (fromAttr !== null && toAttr !== null) {
        const from = parseFloat(fromAttr);
        const to = parseFloat(toAttr);
        const duration = parseFloat(animEl.getAttribute("duration") ?? "1") * 1e3;
        const repeat = parseInt(animEl.getAttribute("repeat") ?? "0");
        const interpolation = animEl.getAttribute("interpolation") ?? "LINEAR";
        const controls = animEl.getAttribute("controls") ?? void 0;
        const fpsAttr = animEl.getAttribute("fps");
        const fps = fpsAttr ? parseInt(fpsAttr) : void 0;
        let elapsed = elapsedMs;
        if (repeat === -1) {
          elapsed = duration > 0 ? elapsed % duration : 0;
        } else if (repeat > 0) {
          const totalDuration = duration * (repeat + 1);
          if (elapsed > totalDuration) elapsed = totalDuration;
          if (elapsed < totalDuration) {
            elapsed = elapsed % duration;
          } else {
            elapsed = duration;
          }
        } else {
          if (elapsed > duration) elapsed = duration;
        }
        if (fps && fps > 0) {
          const frameMs = 1e3 / fps;
          elapsed = Math.floor(elapsed / frameMs) * frameMs;
        }
        let t = duration > 0 ? elapsed / duration : 1;
        t = ease(t, interpolation, controls);
        const value = from + (to - from) * t;
        applyValue(el, target, mode, value);
      }
    } else if (valueExpr) {
      const value = evaluateExpression(valueExpr, expressionCtx);
      applyValue(el, target, mode, Number(value));
    }
  }
}
function applyValue(el, target, mode, value) {
  if (mode === "TO") {
    setAttr(el, target, String(value));
  } else if (mode === "BY") {
    const base = parseFloat(el.getAttribute(target) ?? "0");
    setAttr(el, target, String(base + value));
  }
}

// src/layout.ts
async function renderGroup(ctx, el, renderChild, renderCtx) {
  applyVariants(el, renderCtx.ambient);
  applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs ?? 0);
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const pivotX = parseFloat(el.getAttribute("pivotX") ?? "0.5");
  const pivotY = parseFloat(el.getAttribute("pivotY") ?? "0.5");
  const angle = parseFloat(el.getAttribute("angle") ?? "0");
  const alpha = parseFloat(el.getAttribute("alpha") ?? "255");
  const scaleX = parseFloat(el.getAttribute("scaleX") ?? "1");
  const scaleY = parseFloat(el.getAttribute("scaleY") ?? "1");
  if (alpha <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  const px = pivotX * w;
  const py = pivotY * h;
  ctx.translate(px, py);
  ctx.rotate(angle * Math.PI / 180);
  ctx.scale(scaleX, scaleY);
  ctx.translate(-px, -py);
  ctx.globalAlpha *= alpha / 255;
  applyBlendMode(ctx, el);
  if (hasMasking(el)) {
    await renderWithMasking(ctx, el, w, h, renderChild, renderCtx);
  } else {
    for (const child of el.children) {
      if (child.tagName !== "Variant") {
        await renderChild(ctx, child, renderCtx);
      }
    }
  }
  ctx.restore();
}

// src/conditions.ts
async function renderCondition(ctx, el, renderChild, renderCtx) {
  const namedResults = {};
  const expressionsEl = el.querySelector(":scope > Expressions");
  if (expressionsEl) {
    for (const exprEl of expressionsEl.children) {
      if (exprEl.tagName === "Expression") {
        const name = exprEl.getAttribute("name") ?? "";
        const expr = exprEl.getAttribute("expression") ?? (exprEl.textContent.trim() || "0");
        const augCtx2 = {
          sources: { ...renderCtx.expressionCtx.sources, ...namedResults }
        };
        namedResults[name] = evaluateExpression(expr, augCtx2);
      }
    }
  }
  const augCtx = {
    sources: { ...renderCtx.expressionCtx.sources, ...namedResults }
  };
  const augRenderCtx = { ...renderCtx, expressionCtx: augCtx };
  for (const child of el.children) {
    if (child.tagName === "Compare") {
      const expr = child.getAttribute("expression") ?? "0";
      const result = expr in namedResults ? namedResults[expr] : evaluateExpression(expr, augCtx);
      if (result) {
        for (const grandchild of child.children) {
          await renderChild(ctx, grandchild, augRenderCtx);
        }
        return;
      }
    }
  }
  for (const child of el.children) {
    if (child.tagName === "Default") {
      for (const grandchild of child.children) {
        await renderChild(ctx, grandchild, augRenderCtx);
      }
      return;
    }
  }
}

// src/text.ts
var WEIGHT_MAP = {
  THIN: 100,
  EXTRA_LIGHT: 200,
  LIGHT: 300,
  NORMAL: 400,
  MEDIUM: 500,
  SEMI_BOLD: 600,
  BOLD: 700,
  EXTRA_BOLD: 800,
  BLACK: 900
};
function parseFontElement(fontEl) {
  const family = fontEl?.getAttribute("family") ?? "sans-serif";
  const size = parseFloat(fontEl?.getAttribute("size") ?? "16");
  const color = parseColor(fontEl?.getAttribute("color") ?? "#FFFFFF");
  const weightStr = fontEl?.getAttribute("weight") ?? "NORMAL";
  const weight = WEIGHT_MAP[weightStr] ?? 400;
  const slant = fontEl?.getAttribute("slant");
  const style = slant === "ITALIC" ? "italic" : "normal";
  const letterSpacingAttr = fontEl?.getAttribute("letterSpacing");
  const letterSpacing = letterSpacingAttr ? parseFloat(letterSpacingAttr) : 0;
  const underline = fontEl?.querySelector(":scope > Underline") != null;
  const strikeThrough = fontEl?.querySelector(":scope > StrikeThrough") != null;
  const resolvedFamily = family === "SYNC_TO_DEVICE" ? "sans-serif" : family;
  return { style, weight, size, family: resolvedFamily, color, letterSpacing, underline, strikeThrough };
}
function applyFont(ctx, spec) {
  ctx.font = `${spec.style} ${spec.weight} ${spec.size}px ${spec.family}`;
  ctx.fillStyle = spec.color;
  if (spec.letterSpacing !== 0) {
    const spacingPx = spec.letterSpacing * spec.size;
    ctx.letterSpacing = `${spacingPx}px`;
  } else {
    ctx.letterSpacing = "0px";
  }
}
function resolveTextContent(raw, expressionCtx) {
  return raw.replace(/\[([^\]]+)\]/g, (_match, name) => {
    const val = expressionCtx.sources[name];
    return val !== void 0 ? String(val) : "";
  });
}
function resolveTextAlign(align) {
  switch (align) {
    case "START":
      return "left";
    case "CENTER":
      return "center";
    case "END":
      return "right";
    default:
      return "left";
  }
}
function truncateWithEllipsis(ctx, text, maxWidth) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  const ellipsis = "\u2026";
  let result = text;
  while (result.length > 0 && ctx.measureText(result + ellipsis).width > maxWidth) {
    result = result.slice(0, -1);
  }
  return result + ellipsis;
}
function drawDecorations(ctx, text, x, y, spec, align) {
  if (!spec.underline && !spec.strikeThrough) return;
  const metrics = ctx.measureText(text);
  const textWidth = metrics.width;
  let lineX;
  switch (align) {
    case "center":
      lineX = x - textWidth / 2;
      break;
    case "right":
      lineX = x - textWidth;
      break;
    default:
      lineX = x;
  }
  ctx.save();
  ctx.strokeStyle = spec.color;
  ctx.lineWidth = Math.max(1, spec.size / 14);
  if (spec.underline) {
    const underlineY = y + spec.size * 0.15;
    ctx.beginPath();
    ctx.moveTo(lineX, underlineY);
    ctx.lineTo(lineX + textWidth, underlineY);
    ctx.stroke();
  }
  if (spec.strikeThrough) {
    const strikeY = y - spec.size * 0.25;
    ctx.beginPath();
    ctx.moveTo(lineX, strikeY);
    ctx.lineTo(lineX + textWidth, strikeY);
    ctx.stroke();
  }
  ctx.restore();
}
function renderPartText(ctx, el, renderCtx) {
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const textEl = el.querySelector(":scope > Text");
  if (!textEl) return;
  ctx.save();
  ctx.translate(x, y);
  renderTextElement(ctx, textEl, w, h, renderCtx);
  ctx.restore();
}
function renderTextElement(ctx, textEl, containerWidth, containerHeight, renderCtx) {
  const fontEl = textEl.querySelector(":scope > Font");
  const spec = parseFontElement(fontEl);
  const align = textEl.getAttribute("align") ?? "START";
  const ellipsis = textEl.getAttribute("ellipsis") === "true";
  let rawText = "";
  for (const node of textEl.childNodes) {
    if (node.nodeType === 3) {
      rawText += node.textContent ?? "";
    }
  }
  rawText = rawText.trim();
  const resolvedText = resolveTextContent(rawText, renderCtx.expressionCtx);
  applyFont(ctx, spec);
  const textAlign = resolveTextAlign(align);
  ctx.textAlign = textAlign;
  ctx.textBaseline = "middle";
  let displayText = resolvedText;
  if (ellipsis && containerWidth > 0) {
    displayText = truncateWithEllipsis(ctx, displayText, containerWidth);
  }
  let textX;
  switch (textAlign) {
    case "center":
      textX = containerWidth / 2;
      break;
    case "right":
      textX = containerWidth;
      break;
    default:
      textX = 0;
  }
  const textY = containerHeight / 2;
  ctx.fillText(displayText, textX, textY);
  drawDecorations(ctx, displayText, textX, textY, spec, textAlign);
}
var DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function formatTimeText(format, date, hourFormat) {
  const is24 = hourFormat !== "12";
  const h24 = date.getHours();
  const h12Raw = h24 % 12;
  const h12 = h12Raw === 0 ? 12 : h12Raw;
  const hDisplay24 = h24;
  const hDisplay12 = h12;
  const min = date.getMinutes();
  const sec = date.getSeconds();
  const ampm = h24 >= 12 ? "PM" : "AM";
  const dayName = DAY_NAMES[date.getDay()];
  const tokens = [
    ["hh", String(hDisplay12).padStart(2, "0")],
    ["HH", String(hDisplay24).padStart(2, "0")],
    ["mm", String(min).padStart(2, "0")],
    ["ss", String(sec).padStart(2, "0")],
    ["EEE", dayName],
    ["h", String(hDisplay12)],
    ["H", String(hDisplay24)],
    ["m", String(min)],
    ["s", String(sec)],
    ["a", ampm]
  ];
  let result = format;
  const replacements = [];
  for (const [token, value] of tokens) {
    const placeholder = `\0${replacements.length}\0`;
    replacements.push(value);
    result = result.split(token).join(placeholder);
  }
  for (let i = 0; i < replacements.length; i++) {
    result = result.split(`\0${i}\0`).join(replacements[i]);
  }
  return result;
}
function renderDigitalClock(ctx, el, renderCtx) {
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  ctx.save();
  ctx.translate(x, y);
  for (const child of el.children) {
    if (child.tagName === "TimeText") {
      renderTimeText(ctx, child, w, h, renderCtx);
    }
  }
  ctx.restore();
}
function renderTimeText(ctx, el, parentWidth, parentHeight, renderCtx) {
  applyVariants(el, renderCtx.ambient);
  const alpha = parseFloat(el.getAttribute("alpha") ?? "255");
  if (alpha <= 0) return;
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0") || parentWidth;
  const h = parseFloat(el.getAttribute("height") ?? "0") || parentHeight;
  const format = el.getAttribute("format") ?? "HH:mm";
  const hourFormat = el.getAttribute("hourFormat") ?? "24";
  const align = el.getAttribute("align") ?? "START";
  const utcTimestamp = renderCtx.expressionCtx.sources["UTC_TIMESTAMP"];
  const date = typeof utcTimestamp === "number" ? new Date(utcTimestamp * 1e3) : /* @__PURE__ */ new Date();
  const formattedText = formatTimeText(format, date, hourFormat);
  const fontEl = el.querySelector(":scope > Font");
  const spec = parseFontElement(fontEl);
  const sizeAttr = el.getAttribute("size");
  if (sizeAttr) {
    spec.size = parseFloat(sizeAttr);
  }
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= alpha / 255;
  applyFont(ctx, spec);
  const textAlign = resolveTextAlign(align);
  ctx.textAlign = textAlign;
  ctx.textBaseline = "middle";
  let textX;
  switch (textAlign) {
    case "center":
      textX = w / 2;
      break;
    case "right":
      textX = w;
      break;
    default:
      textX = 0;
  }
  const textY = h / 2;
  ctx.fillText(formattedText, textX, textY);
  drawDecorations(ctx, formattedText, textX, textY, spec, textAlign);
  ctx.restore();
}

// src/images.ts
var imageCaches = /* @__PURE__ */ new WeakMap();
async function renderPartImage(ctx, el, renderCtx, assets) {
  applyVariants(el, renderCtx.ambient);
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const imageEl = findImageChild(el);
  if (!imageEl) return;
  const resource = imageEl.getAttribute("resource") ?? "";
  if (!resource) return;
  const bitmap = await getOrDecodeImage(resource, assets);
  if (!bitmap) return;
  ctx.save();
  ctx.drawImage(bitmap, x, y, w, h);
  ctx.restore();
}
function findImageChild(el) {
  for (const child of el.children) {
    if (child.tagName === "Image") return child;
  }
  return null;
}
async function getOrDecodeImage(resource, assets) {
  // Keyed by the face's asset map: faces may share resource names.
  let cache = imageCaches.get(assets);
  if (!cache) imageCaches.set(assets, cache = /* @__PURE__ */ new Map());
  if (cache.has(resource)) {
    return cache.get(resource);
  }
  const buffer = assets.get(resource);
  if (!buffer) return null;
  const blob = new Blob([buffer]);
  const bitmap = await createImageBitmap(blob);
  cache.set(resource, bitmap);
  return bitmap;
}

// src/clock.ts
async function renderAnalogClock(ctx, el, renderChild, renderCtx) {
  applyVariants(el, renderCtx.ambient);
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const alpha = parseFloat(el.getAttribute("alpha") ?? "255");
  if (alpha <= 0) return;
  const sources = renderCtx.expressionCtx.sources;
  const hour = sources.HOUR_0_23 ?? 0;
  const minute = sources.MINUTE ?? 0;
  const second = sources.SECOND ?? 0;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= alpha / 255;
  for (const child of el.children) {
    const tag = child.tagName;
    if (tag === "HourHand" || tag === "MinuteHand" || tag === "SecondHand") {
      let angle;
      if (tag === "HourHand") {
        angle = (hour % 12 + minute / 60) * 30;
      } else if (tag === "MinuteHand") {
        angle = (minute + second / 60) * 6;
      } else {
        angle = second * 6;
      }
      await renderHand(ctx, child, angle, renderChild, renderCtx);
    } else if (tag !== "Variant") {
      await renderChild(ctx, child, renderCtx);
    }
  }
  ctx.restore();
}
function resolveExprRef(value, expressionCtx) {
  if (!value?.includes("[")) return value;
  return value.replace(/\[([^\]]+)\]/g, (_, name) => {
    const val = expressionCtx.sources[name];
    return val !== void 0 ? String(val) : "#000000";
  });
}
async function drawTintedImage(ctx, bitmap, w, h, tintColor) {
  if (!tintColor) {
    ctx.drawImage(bitmap, 0, 0, w, h);
    return;
  }
  const offscreen = new OffscreenCanvas(w, h);
  const offCtx = offscreen.getContext("2d");
  offCtx.drawImage(bitmap, 0, 0, w, h);
  offCtx.globalCompositeOperation = "source-in";
  offCtx.fillStyle = parseColor(tintColor);
  offCtx.fillRect(0, 0, w, h);
  ctx.drawImage(offscreen, 0, 0);
}
async function renderHand(ctx, el, angle, renderChild, renderCtx) {
  applyVariants(el, renderCtx.ambient);
  const alpha = parseFloat(el.getAttribute("alpha") ?? "255");
  if (alpha <= 0) return;
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const pivotX = parseFloat(el.getAttribute("pivotX") ?? "0.5");
  const pivotY = parseFloat(el.getAttribute("pivotY") ?? "0.5");
  const tintColor = resolveExprRef(el.getAttribute("tintColor"), renderCtx.expressionCtx);
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= alpha / 255;
  const px = pivotX * w;
  const py = pivotY * h;
  ctx.translate(px, py);
  ctx.rotate(angle * Math.PI / 180);
  ctx.translate(-px, -py);
  const resource = el.getAttribute("resource");
  if (resource) {
    const bitmap = await getOrDecodeImage(resource, renderCtx.assets);
    if (bitmap) {
      await drawTintedImage(ctx, bitmap, w, h, tintColor);
    }
  }
  for (const child of el.children) {
    if (child.tagName !== "Variant") {
      await renderChild(ctx, child, renderCtx);
    }
  }
  ctx.restore();
}

// src/shapes.ts
function resolveColorExprs(el, expressionCtx) {
  for (const child of el.children) {
    if (child.tagName !== "Fill" && child.tagName !== "Stroke") continue;
    const color = child.getAttribute("color");
    if (!color?.includes("[")) continue;
    const resolved = color.replace(/\[([^\]]+)\]/g, (_, name) => {
      const val = expressionCtx.sources[name];
      return val !== void 0 ? String(val) : "#000000";
    });
    setAttr(child, "color", resolved);
  }
}
async function renderElement(ctx, el, renderCtx) {
  const tag = el.tagName;
  switch (tag) {
    case "Group":
    case "PartDraw":
      await renderGroup(ctx, el, renderElement, renderCtx);
      break;
    case "Condition":
      await renderCondition(ctx, el, renderElement, renderCtx);
      break;
    case "Arc":
      applyVariants(el, renderCtx.ambient);
      applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs);
      resolveColorExprs(el, renderCtx.expressionCtx);
      applyBlendMode(ctx, el);
      renderArc(ctx, el);
      break;
    case "Rectangle":
      applyVariants(el, renderCtx.ambient);
      applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs);
      resolveColorExprs(el, renderCtx.expressionCtx);
      applyBlendMode(ctx, el);
      renderRectangle(ctx, el);
      break;
    case "RoundRectangle":
      applyVariants(el, renderCtx.ambient);
      applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs);
      resolveColorExprs(el, renderCtx.expressionCtx);
      applyBlendMode(ctx, el);
      renderRoundRectangle(ctx, el);
      break;
    case "Ellipse":
      applyVariants(el, renderCtx.ambient);
      applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs);
      resolveColorExprs(el, renderCtx.expressionCtx);
      applyBlendMode(ctx, el);
      renderEllipse(ctx, el);
      break;
    case "Line":
      applyVariants(el, renderCtx.ambient);
      applyTransforms(el, renderCtx.expressionCtx, renderCtx.elapsedMs);
      resolveColorExprs(el, renderCtx.expressionCtx);
      applyBlendMode(ctx, el);
      renderLine(ctx, el);
      break;
    case "PartText":
      renderPartText(ctx, el, renderCtx);
      break;
    case "DigitalClock":
      renderDigitalClock(ctx, el, renderCtx);
      break;
    case "PartImage":
      await renderPartImage(ctx, el, renderCtx, renderCtx.assets);
      break;
    case "AnalogClock":
      await renderAnalogClock(ctx, el, renderElement, renderCtx);
      break;
  }
}
function renderRectangle(ctx, el) {
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  applyFill(ctx, el);
  applyStroke(ctx, el);
}
function renderRoundRectangle(ctx, el) {
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const rx = parseFloat(el.getAttribute("cornerRadiusX") ?? "0");
  const ry = parseFloat(el.getAttribute("cornerRadiusY") ?? rx.toString());
  ctx.beginPath();
  const radius = { x: rx, y: ry };
  ctx.roundRect(x, y, w, h, [radius, radius, radius, radius]);
  applyFill(ctx, el);
  applyStroke(ctx, el);
}
function renderArc(ctx, el) {
  const cx = parseFloat(el.getAttribute("centerX") ?? "0");
  const cy = parseFloat(el.getAttribute("centerY") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  const startAngle = parseFloat(el.getAttribute("startAngle") ?? "0");
  const endAngle = parseFloat(el.getAttribute("endAngle") ?? "360");
  const direction = el.getAttribute("direction") ?? "CLOCKWISE";
  const startRad = (startAngle - 90) * Math.PI / 180;
  const endRad = (endAngle - 90) * Math.PI / 180;
  const counterclockwise = direction === "COUNTER_CLOCKWISE";
  ctx.beginPath();
  if (w === h) {
    ctx.arc(cx, cy, w / 2, startRad, endRad, counterclockwise);
  } else {
    ctx.ellipse(cx, cy, w / 2, h / 2, 0, startRad, endRad, counterclockwise);
  }
  applyFill(ctx, el);
  applyStroke(ctx, el);
}
function renderEllipse(ctx, el) {
  const x = parseFloat(el.getAttribute("x") ?? "0");
  const y = parseFloat(el.getAttribute("y") ?? "0");
  const w = parseFloat(el.getAttribute("width") ?? "0");
  const h = parseFloat(el.getAttribute("height") ?? "0");
  ctx.beginPath();
  ctx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
  applyFill(ctx, el);
  applyStroke(ctx, el);
}
function renderLine(ctx, el) {
  const x1 = parseFloat(el.getAttribute("startX") ?? "0");
  const y1 = parseFloat(el.getAttribute("startY") ?? "0");
  const x2 = parseFloat(el.getAttribute("endX") ?? "0");
  const y2 = parseFloat(el.getAttribute("endY") ?? "0");
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  applyStroke(ctx, el);
}

// src/index.ts
function parseUserConfigurations(doc, userConfig) {
  const result = {};
  const userConfEl = doc.querySelector("UserConfigurations");
  if (!userConfEl) return result;
  for (const child of userConfEl.children) {
    const id = child.getAttribute("id");
    if (!id) continue;
    if (child.tagName === "ColorConfiguration") {
      const defaultValue = child.getAttribute("defaultValue") ?? "0";
      const selectedId = userConfig?.[id] !== void 0 ? String(userConfig[id]) : defaultValue;
      for (const opt of child.querySelectorAll("ColorOption")) {
        if (opt.getAttribute("id") === selectedId) {
          const colors = (opt.getAttribute("colors") ?? "").split(/\s+/).filter(Boolean);
          colors.forEach((color, i) => {
            result[`${id}.${i}`] = color;
          });
          break;
        }
      }
    } else if (child.tagName === "ListConfiguration") {
      const defaultValue = child.getAttribute("defaultValue") ?? "0";
      result[id] = userConfig?.[id] !== void 0 ? String(userConfig[id]) : defaultValue;
    } else if (child.tagName === "BooleanConfiguration") {
      const defaultValue = child.getAttribute("defaultValue") ?? "TRUE";
      const val = userConfig?.[id] !== void 0 ? String(userConfig[id]) : defaultValue;
      result[id] = val === "TRUE" ? 1 : 0;
    }
  }
  return result;
}
async function renderFrame(canvas, ctx, doc, options, elapsedMs, time) {
  const root = doc.documentElement;
  const width = parseInt(root.getAttribute("width") ?? "450", 10);
  const height = parseInt(root.getAttribute("height") ?? "450", 10);
  const clipShape = root.getAttribute("clipShape");
  const metadata = /* @__PURE__ */ new Map();
  const metaElements = root.querySelectorAll("Metadata");
  for (const el of metaElements) {
    const key = el.getAttribute("key");
    const value = el.getAttribute("value");
    if (key !== null && value !== null) {
      metadata.set(key, value);
    }
  }
  ctx.resetTransform?.();
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
  if (clipShape === "CIRCLE") {
    ctx.beginPath();
    ctx.arc(width / 2, height / 2, Math.min(width, height) / 2, 0, Math.PI * 2);
    ctx.clip();
  }
  const scene = root.querySelector("Scene");
  const backgroundColor = scene?.getAttribute("backgroundColor") ?? "#000000";
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, width, height);
  const parsedConfig = parseUserConfigurations(doc, options.configuration);
  const mergedConfig = { ...parsedConfig, ...options.configuration };
  const expressionCtx = buildDataSources(time, mergedConfig, true);
  const renderCtx = {
    expressionCtx,
    ambient: options.ambient ?? false,
    assets: options.assets ?? /* @__PURE__ */ new Map(),
    elapsedMs
  };
  if (scene) {
    for (const child of scene.children) {
      await renderElement(ctx, child, renderCtx);
    }
  }
  ctx.restore();
  return metadata;
}
async function renderWatchFace(canvas, options) {
  const doc = new DOMParser().parseFromString(options.xml, "text/xml");
  const root = doc.documentElement;
  if (root.tagName === "parsererror" || root.querySelector("parsererror")) {
    throw new Error("Invalid WFF XML: " + root.textContent?.slice(0, 200));
  }
  const xmlWidth = parseInt(root.getAttribute("width") ?? "450", 10);
  const xmlHeight = parseInt(root.getAttribute("height") ?? "450", 10);
  const width = options.width ?? xmlWidth;
  const height = options.height ?? xmlHeight;
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    const metadata2 = /* @__PURE__ */ new Map();
    return { metadata: metadata2 };
  }
  if (options.animate) {
    const startTime = performance.now();
    let animFrameId;
    let metadata2 = /* @__PURE__ */ new Map();
    const frame = async () => {
      const now = /* @__PURE__ */ new Date();
      const elapsed = performance.now() - startTime;
      const freshDoc2 = new DOMParser().parseFromString(options.xml, "text/xml");
      if (freshDoc2.documentElement.tagName === "parsererror") return;
      metadata2 = await renderFrame(canvas, ctx, freshDoc2, options, elapsed, now);
      animFrameId = requestAnimationFrame(() => {
        void frame();
      });
    };
    animFrameId = requestAnimationFrame(() => {
      void frame();
    });
    const freshDoc = new DOMParser().parseFromString(options.xml, "text/xml");
    const initialMetadata = await renderFrame(
      canvas,
      ctx,
      freshDoc,
      options,
      0,
      options.time ?? /* @__PURE__ */ new Date()
    );
    return {
      metadata: initialMetadata,
      stop: () => cancelAnimationFrame(animFrameId)
    };
  }
  const metadata = await renderFrame(canvas, ctx, doc, options, 0, options.time ?? /* @__PURE__ */ new Date());
  return { metadata };
}
const frameBuffers = /* @__PURE__ */ new WeakMap();
const parsedFaces = /* @__PURE__ */ new Map();
async function renderWatchFaceFrame(canvas, options, elapsedMs, time) {
  let template = parsedFaces.get(options.xml);
  if (!template) {
    template = new DOMParser().parseFromString(options.xml, "text/xml");
    if (parsedFaces.size > 32) parsedFaces.clear();
    parsedFaces.set(options.xml, template);
  }
  if (template.documentElement.tagName === "parsererror") return;
  // Render into the cached document and undo its attribute writes afterwards;
  // only if that document is mid-frame already (overlapping calls) use a copy.
  const reuse = !template.__journal;
  const doc = reuse ? template : template.cloneNode(true);
  if (reuse) template.__journal = [];
  try {
    await drawFrame(canvas, options, elapsedMs, time, doc);
  } finally {
    if (reuse) undoJournal(template);
  }
}
async function drawFrame(canvas, options, elapsedMs, time, doc) {
  const width = options.width ?? 450;
  const height = options.height ?? 450;
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;
  // Draw off screen and copy in one step: renderFrame awaits image work, and
  // drawing straight to the visible canvas would show half-finished frames.
  let buffer = frameBuffers.get(canvas);
  if (!buffer) frameBuffers.set(canvas, buffer = document.createElement("canvas"));
  buffer.width = width;
  buffer.height = height;
  const bufferCtx = buffer.getContext("2d");
  await renderFrame(buffer, bufferCtx, doc, options, elapsedMs, time ?? /* @__PURE__ */ new Date());
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(buffer, 0, 0);
}
export {
  renderWatchFace,
  renderWatchFaceFrame
};
