// Swipeable slide decks: one idea per slide.
// Move between slides with a two-finger trackpad swipe, the ← → keys, the arrow buttons, or a heading pill.
// Markup: <div class="deck"><nav class="deck-nav"></nav><div class="deck-track"><section class="slide" data-title="…">…</section>…</div></div>

function initDeck(root) {
    const track = root.querySelector(".deck-track");
    const slides = [...track.children];
    const pad = parseFloat(getComputedStyle(track).paddingTop) + parseFloat(getComputedStyle(track).paddingBottom);
    let index = -1, frame = 0;

    const prev = h("button", { class: "deck-arrow", type: "button", "aria-label": "Previous slide", title: "Previous (←)", onclick: () => go(index - 1) }, "‹");
    const next = h("button", { class: "deck-arrow", type: "button", "aria-label": "Next slide", title: "Next (→)", onclick: () => go(index + 1) }, "›");
    const pills = slides.map((slide, i) => {
        slide.setAttribute("aria-label", slide.dataset.title);
        return h("button", { class: "deck-pill", type: "button", role: "tab", onclick: () => go(i) }, h("span", { class: "n" }, i + 1), slide.dataset.title);
    });
    const pillBox = h("div", { class: "deck-pills", role: "tablist" }, ...pills);
    root.querySelector(".deck-nav").replaceChildren(prev, pillBox, next);

    let settle = 0;
    function go(i) {
        i = Math.max(0, Math.min(slides.length - 1, i));
        const left = slides[i].offsetLeft, start = track.scrollLeft;
        track.scrollTo({ left, behavior: "smooth" });
        // If the smooth scroll never started (some browsers skip it when not drawing frames), jump instead.
        clearTimeout(settle);
        settle = setTimeout(() => { if (track.scrollLeft === start && start !== left) track.scrollLeft = left; update(); }, 700);
    }

    function fit() {
        const height = slides[index]?.offsetHeight;
        if (height) track.style.height = height + pad + "px";
    }

    function update() {
        const x = track.scrollLeft;
        let best = 0;
        slides.forEach((s, i) => { if (Math.abs(s.offsetLeft - x) < Math.abs(slides[best].offsetLeft - x)) best = i; });
        if (best === index) return;
        index = best;
        pills.forEach((p, i) => p.setAttribute("aria-selected", i === index));
        slides.forEach((s, i) => s.setAttribute("aria-hidden", i !== index));
        prev.disabled = index === 0;
        next.disabled = index === slides.length - 1;
        const pill = pills[index];
        if (pillBox.scrollWidth > pillBox.clientWidth) pillBox.scrollTo({ left: pill.offsetLeft - 40, behavior: "smooth" });
        fit();
    }

    track.addEventListener("scroll", () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(update); }, { passive: true });
    track.addEventListener("scrollend", update);
    // Slides grow when charts finish drawing or a tab is shown, so keep the deck as tall as the slide in view.
    const watch = new ResizeObserver(fit);
    slides.forEach((s) => watch.observe(s));
    root._deck = { go, get index() { return index; } };
    update();
}

document.querySelectorAll(".deck").forEach(initDeck);

// ← and → move the deck nearest the middle of the screen, unless the person is typing.
document.addEventListener("keydown", (e) => {
    if ((e.key !== "ArrowLeft" && e.key !== "ArrowRight") || e.altKey || e.metaKey || e.ctrlKey || e.shiftKey) return;
    if (e.target.closest?.("input, textarea, select, [contenteditable]")) return;
    const middle = innerHeight / 2;
    let best = null, bestDistance = Infinity;
    for (const deck of document.querySelectorAll(".deck")) {
        const r = deck.getBoundingClientRect();
        if (!r.height || r.bottom < 0 || r.top > innerHeight) continue;
        const distance = r.top <= middle && r.bottom >= middle ? 0 : Math.min(Math.abs(r.top - middle), Math.abs(r.bottom - middle));
        if (distance < bestDistance) { best = deck; bestDistance = distance; }
    }
    if (!best) return;
    e.preventDefault();
    best._deck.go(best._deck.index + (e.key === "ArrowRight" ? 1 : -1));
});
