// Small dependency-free SVG chart helpers (works offline during a demo).
const SVGNS = "http://www.w3.org/2000/svg";

function el(tag, attrs = {}, parent) {
    const node = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (parent) parent.appendChild(node);
    return node;
}

function h(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === "class") node.className = v;
        else if (k === "style") node.style.cssText = v;
        else if (k === "html") node.innerHTML = v;
        else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v);
    }
    for (const child of children.flat()) {
        if (child == null || child === false) continue;
        node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
}

const tip = {
    node: null,
    show(event, html) {
        this.node = this.node || document.getElementById("tooltip");
        this.node.innerHTML = html;
        this.node.hidden = false;
        this.move(event);
    },
    move(event) {
        if (!this.node || this.node.hidden) return;
        const pad = 14, r = this.node.getBoundingClientRect();
        let x = event.clientX + pad, y = event.clientY + pad;
        if (x + r.width > innerWidth - 8) x = event.clientX - r.width - pad;
        if (y + r.height > innerHeight - 8) y = event.clientY - r.height - pad;
        this.node.style.left = x + "px";
        this.node.style.top = y + "px";
    },
    hide() { if (this.node) this.node.hidden = true; },
};

function hover(target, html) {
    target.addEventListener("mouseenter", (e) => tip.show(e, typeof html === "function" ? html() : html));
    target.addEventListener("mousemove", (e) => tip.move(e));
    target.addEventListener("mouseleave", () => tip.hide());
}

// Horizontal bars, one per item, labelled directly.
function hbarChart(container, items, { max, format = (v) => v, sub } = {}) {
    container.replaceChildren();
    const top = max ?? Math.max(...items.map((i) => i.value), 1e-9);
    for (const item of items) {
        const fill = h("div", { class: "hbar-fill", style: `width:0;background:${item.color}` });
        const row = h("div", { class: "hbar-row" },
            h("div", { class: "hbar-label" }, h("i", { class: "swatch", style: `background:${item.color}` }), item.label),
            h("div", { class: "hbar-track" }, fill),
            h("div", { class: "hbar-value" }, format(item.value), sub ? h("small", {}, sub(item)) : null));
        hover(row, `<b>${item.label}</b>${item.tip || format(item.value)}`);
        container.append(row);
        requestAnimationFrame(() => requestAnimationFrame(() => {
            fill.style.width = top ? Math.max(0, (item.value / top) * 100) + "%" : "0";
        }));
    }
}

// Line chart with a crosshair tooltip. series: [{name, color, values:[...] }], x: labels.
function lineChart(container, { x, series, yMin = 0, yMax = 1, yFormat = (v) => v, xTitle = "", height = 240, markers = [] }) {
    container.replaceChildren();
    if (series.length > 1) container.append(h("div", { class: "chart-legend" }, ...series.map((s) => h("span", {}, h("i", { class: "swatch", style: `background:${s.color}` }), s.name))));
    const W = 560, H = height, m = { l: 44, r: 16, t: 12, b: 38 };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "svg-chart", role: "img" }, container);
    const px = (i) => m.l + (i / (x.length - 1)) * (W - m.l - m.r);
    const py = (v) => m.t + (1 - (v - yMin) / (yMax - yMin)) * (H - m.t - m.b);
    for (let k = 0; k <= 4; k++) {
        const v = yMin + (k / 4) * (yMax - yMin);
        el("line", { x1: m.l, x2: W - m.r, y1: py(v), y2: py(v), stroke: k ? "var(--grid)" : "var(--axis)", "stroke-width": 1 }, svg);
        el("text", { x: m.l - 8, y: py(v) + 4, "text-anchor": "end" }, svg).textContent = yFormat(v);
    }
    const step = Math.ceil(x.length / 10);
    x.forEach((label, i) => {
        if (i % step === 0 || i === x.length - 1) el("text", { x: px(i), y: H - m.b + 18, "text-anchor": "middle" }, svg).textContent = label;
    });
    if (xTitle) el("text", { x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", class: "axis-label" }, svg).textContent = xTitle;
    for (const mk of markers) {
        el("line", { x1: px(mk.index), x2: px(mk.index), y1: m.t, y2: H - m.b, stroke: "var(--ink-2)", "stroke-dasharray": "3 3" }, svg);
        el("text", { x: px(mk.index) - 4, y: H - m.b - 6, "text-anchor": "end", class: "axis-label" }, svg).textContent = mk.label;
    }
    for (const s of series) {
        const d = s.values.map((v, i) => `${i ? "L" : "M"}${px(i)},${py(v)}`).join("");
        const path = el("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
        const len = path.getTotalLength ? path.getTotalLength() : 1000;
        path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
        path.style.transition = "stroke-dashoffset 1.2s ease";
        requestAnimationFrame(() => requestAnimationFrame(() => (path.style.strokeDashoffset = 0)));
        const last = s.values.length - 1;
        if (s.endLabel) {
            el("text", { x: px(last) - 4, y: py(s.values[last]) - 8, "text-anchor": "end", style: `fill:var(--ink-2);font-weight:600` }, svg).textContent = s.endLabel || s.name;
        }
    }
    const cross = el("line", { y1: m.t, y2: H - m.b, stroke: "var(--axis)", visibility: "hidden" }, svg);
    const dots = series.map((s) => el("circle", { r: 4.5, fill: s.color, stroke: "#fff", "stroke-width": 2, visibility: "hidden" }, svg));
    const hit = el("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", (e) => {
        const r = svg.getBoundingClientRect();
        const sx = ((e.clientX - r.left) / r.width) * W;
        const i = Math.max(0, Math.min(x.length - 1, Math.round(((sx - m.l) / (W - m.l - m.r)) * (x.length - 1))));
        cross.setAttribute("x1", px(i)); cross.setAttribute("x2", px(i)); cross.setAttribute("visibility", "visible");
        series.forEach((s, k) => { dots[k].setAttribute("cx", px(i)); dots[k].setAttribute("cy", py(s.values[i])); dots[k].setAttribute("visibility", "visible"); });
        tip.show(e, `<b>${xTitle ? xTitle + " " : ""}${x[i]}</b>` + series.map((s) => `<span style="color:${s.color}">●</span> ${s.name}: ${yFormat(s.values[i])}`).join("<br>"));
    });
    hit.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); dots.forEach((d) => d.setAttribute("visibility", "hidden")); tip.hide(); });
}

// Confusion-matrix style heatmap (single blue ramp).
function heatmap(container, { rows, cols, matrix, rowTitle = "Actual", colTitle = "Predicted" }) {
    container.replaceChildren();
    const cell = 64, m = { l: 150, t: 20, b: 110 };
    const W = m.l + cols.length * cell + 10, H = m.t + rows.length * cell + m.b;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "svg-chart", style: `max-width:${W}px` }, container);
    const max = Math.max(...matrix.flat());
    const ramp = ["#eef4fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];
    matrix.forEach((row, i) => row.forEach((v, j) => {
        const k = v === 0 ? 0 : Math.min(ramp.length - 1, 1 + Math.floor((v / max) * (ramp.length - 1.01)));
        const r = el("rect", { x: m.l + j * cell + 1, y: m.t + i * cell + 1, width: cell - 2, height: cell - 2, rx: 4, fill: ramp[k] }, svg);
        const t = el("text", { x: m.l + j * cell + cell / 2, y: m.t + i * cell + cell / 2 + 5, "text-anchor": "middle", style: `font-size:15px;font-weight:700;fill:${k >= 4 ? "#fff" : "#0f1115"}` }, svg);
        t.textContent = v;
        hover(r, `<b>${v} messages</b>Actually: ${rows[i]}<br>Model said: ${cols[j]}`);
    }));
    rows.forEach((label, i) => { el("text", { x: m.l - 8, y: m.t + i * cell + cell / 2 + 4, "text-anchor": "end", class: "axis-label" }, svg).textContent = label; });
    cols.forEach((label, j) => {
        const x = m.l + j * cell + cell / 2, y = m.t + rows.length * cell + 10;
        el("text", { x, y, transform: `rotate(-40 ${x} ${y})`, "text-anchor": "end", class: "axis-label" }, svg).textContent = label;
    });
    el("text", { x: 12, y: m.t + (rows.length * cell) / 2, transform: `rotate(-90 12 ${m.t + (rows.length * cell) / 2})`, "text-anchor": "middle", class: "axis-label", style: "font-weight:650" }, svg).textContent = rowTitle;
    el("text", { x: m.l + (cols.length * cell) / 2, y: H - 6, "text-anchor": "middle", class: "axis-label", style: "font-weight:650" }, svg).textContent = colTitle;
}

// Two-group histogram of risk scores with threshold lines (small multiples: one row per group).
function riskHistogram(container, { groups, thresholds, bins = 20 }) {
    container.replaceChildren();
    const W = 560, rowH = 110, m = { l: 90, r: 16, t: 10, b: 40 };
    const H = m.t + groups.length * rowH + m.b;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "svg-chart", style: "max-width:720px" }, container);
    const px = (v) => m.l + v * (W - m.l - m.r);
    const bw = (W - m.l - m.r) / bins;
    groups.forEach((g, gi) => {
        const counts = Array(bins).fill(0);
        g.values.forEach((v) => counts[Math.min(bins - 1, Math.floor(v * bins))]++);
        const max = Math.max(...counts, 1);
        const base = m.t + (gi + 1) * rowH - 8;
        el("line", { x1: m.l, x2: W - m.r, y1: base, y2: base, stroke: "var(--axis)" }, svg);
        el("text", { x: m.l - 10, y: base - rowH / 2 + 10, "text-anchor": "end", class: "axis-label", style: "font-weight:650" }, svg).textContent = g.name;
        counts.forEach((c, i) => {
            if (!c) return;
            const hgt = (c / max) * (rowH - 24);
            const r = el("rect", { x: m.l + i * bw + 1, y: base - hgt, width: bw - 2, height: hgt, rx: 2, fill: g.color }, svg);
            hover(r, `<b>${g.name}</b>${c} messages with risk ${(i / bins).toFixed(2)}–${((i + 1) / bins).toFixed(2)}`);
        });
    });
    for (const t of thresholds) {
        el("line", { x1: px(t.value), x2: px(t.value), y1: m.t, y2: H - m.b, stroke: t.color, "stroke-width": 1.5, "stroke-dasharray": "4 3" }, svg);
        el("text", { x: px(t.value) + 4, y: m.t + 10, class: "axis-label", style: "font-weight:600" }, svg).textContent = t.label;
    }
    for (let k = 0; k <= 4; k++) el("text", { x: px(k / 4), y: H - m.b + 18, "text-anchor": "middle" }, svg).textContent = (k / 4).toFixed(2);
    el("text", { x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", class: "axis-label" }, svg).textContent = "Risk score (1 − chance of being safe)";
}

window.Charts = { el, h, hover, tip, hbarChart, lineChart, heatmap, riskHistogram };
