// DTAK slide chrome + Reveal init. Load after reveal.js and its notes plugin.
//
// Every slide gets: top accent bar, footer (UPC mark left · rule · DTAK short logo right), page number
// bottom-right ("h" or "h.v", 1-based, also in the PDF).
//   class="section"   dark slide: navy background, negative UPC and DTAK marks, white text
//   class="title"     title slide: centred
//   class="nochrome"  no bar and no footer (number only)
(() => {
  const base = document.currentScript.src.replace(/[^/]*$/, '');  // theme/
  const NAVY = '#0A2A4F';

  const slides = [];
  document.querySelectorAll('.reveal .slides > section').forEach((top, h) => {
    const inner = top.querySelectorAll(':scope > section');
    if (inner.length) {
      top.classList.add('stack');
      inner.forEach((s, v) => slides.push([s, `${h + 1}.${v + 1}`]));
    } else slides.push([top, `${h + 1}`]);
  });

  for (const [s, num] of slides) {
    const dark = s.classList.contains('section');
    if (dark) s.dataset.backgroundColor = NAVY;
    s.insertAdjacentHTML('beforeend', `<div class="chrome"><i class="bar"></i>
      <div class="foot">
        <img src="${base}logos/upc-barcelonatech${dark ? '-neg' : ''}.svg" alt="UPC BarcelonaTech">
        <i class="rule"></i>
        <img src="${base}logos/dtak${dark ? '-neg' : ''}.svg" alt="DTAK">
      </div>
      <span class="num">${num}</span></div>`);
  }

  Reveal.initialize({
    width: 1280, height: 720, margin: 0, center: false, hash: true,
    transition: 'fade', transitionSpeed: 'fast', controls: false, progress: false, pdfSeparateFragments: false,
    plugins: [RevealNotes],
  });
})();
