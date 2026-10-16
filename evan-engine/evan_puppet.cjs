// Articulated vector prototype based on Evan's supplied character references.
// Original vector artwork, not a cutout or edit of the reference bitmaps.
const {renderScene} = require('./scene_graphics.cjs');
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const clamp = (v,a,b)=>Math.max(a,Math.min(b,v));
const ease = x => {x=clamp(x,0,1);return x*x*(3-2*x)};
const pulse = (t,a,b) => ease((t-a)/.45)*(1-ease((t-b)/.45));

function mouth(shape) {
  const stroke='stroke="#793e30" stroke-width="2.5" stroke-linejoin="round"';
  if(shape==='X'||shape==='A') return `<path d="M-24 0 Q0 7 25 -2" fill="none" ${stroke}/><path d="M-13 9 Q0 12 13 8" stroke="#c97e62" fill="none" stroke-width="2"/>`;
  if(shape==='E'||shape==='F') return `<ellipse cx="2" cy="5" rx="${shape==='E'?12:9}" ry="${shape==='E'?16:10}" fill="#4a2026" ${stroke}/><ellipse cx="3" cy="14" rx="7" ry="4" fill="#cf7477"/>`;
  if(shape==='G') return `<path d="M-23 0 Q0 -6 23 0 Q12 15 -12 11Z" fill="#56252b" ${stroke}/><path d="M-20 0 Q0 -3 20 0 L13 6 -15 6Z" fill="#fff8ed"/>`;
  const open = shape==='D'?23:shape==='C'?15:shape==='H'?17:9;
  return `<path d="M-26 -1 Q0 -8 26 -1 Q21 ${open+11} 0 ${open+7} Q-21 ${open+8} -26 -1Z" fill="#462029" ${stroke}/><path d="M-23 -1 Q0 -5 23 -1 L19 7 Q0 10 -19 7Z" fill="#fffaf0"/><path d="M-14 ${open+2} Q0 ${open-8} 15 ${open+2} Q0 ${open+9} -14 ${open+2}" fill="#d77d80"/>`;
}

function hand(pointing=false) {
  return pointing
    ? `<path d="M-19 5 Q-23 -7 -16 -16 L-12 -34 Q-9 -45 -3 -40 L-2 -13 L5 -21 Q10 -25 13 -17 L18 -16 Q25 -17 25 -8 L28 -3 Q31 9 22 19 L8 30 -12 25Z" fill="url(#skin)" stroke="#392a2c" stroke-width="3"/><path d="M-2 -13 L-1 7 M12 -16 L11 4 M22 -7 L19 8" fill="none" stroke="#bf785c" stroke-width="2"/>`
    : `<path d="M-19 7 L-34 -4 Q-43 -13 -35 -17 L-17 -7 L-28 -25 Q-31 -34 -23 -32 L-8 -13 L-15 -36 Q-15 -45 -8 -40 L3 -16 L2 -40 Q4 -48 10 -39 L15 -13 L22 -29 Q28 -34 31 -27 L27 5 Q28 19 13 31 L-8 29Z" fill="url(#skin)" stroke="#392a2c" stroke-width="3"/><path d="M-15 8 Q1 0 17 6 M4 -7 L9 11" stroke="#bd775c" stroke-width="2" fill="none"/>`;
}

function arm(side, shoulder, elbow, point) {
  const mirror=side==='left'?-1:1;
  return `<g data-bone="${side}-upper-arm" transform="translate(${mirror*86},730) rotate(${-mirror*shoulder})">
    <path d="M-29 -10 Q-9 -24 21 -10 L29 114 Q3 136 -27 114 L-35 30Z" fill="url(#shirt)" stroke="#121b2b" stroke-width="4"/>
    <path d="M-22 30 L-8 91 21 108 M-20 104 L6 114" fill="none" stroke="#52617b" stroke-width="3"/>
    <g data-bone="${side}-forearm" transform="translate(0,112) rotate(${mirror*elbow})">
      <path d="M-25 -10 Q0 -1 24 -10 L20 93 Q0 107 -21 94Z" fill="url(#shirt)" stroke="#121b2b" stroke-width="4"/>
      <path d="M-24 80 L23 78 23 100 -22 102Z" fill="#24334e" stroke="#131d30" stroke-width="3"/>
      <g transform="translate(0,122) rotate(180)">${hand(point)}</g>
    </g>
  </g>`;
}

function strength(t, data, kind) {
  if (!Array.isArray(data.gestures)) return 0;
  return Math.max(0, ...data.gestures.filter(g=>g.kind===kind && t>=g.start-.36 && t<=g.end+.36)
    .map(g=>pulse(t,g.start-.20,g.end+.20)));
}

function render(t, data) {
  const cue = data.mouthCues.find(c=>t>=c.start&&t<c.end)?.value || 'X';
  const talk=cue==='X'?0:1;
  const pointing=strength(t,data,'point'), presenting=strength(t,data,'present');
  const emphasis=strength(t,data,'emphasis'), pinch=strength(t,data,'pinch');
  const ending=strength(t,data,'outro');
  const lean=1.2*Math.sin(t*1.3)+1.8*pointing+.7*emphasis;
  const bob=2*Math.sin(t*2.1);
  const head=1.5*Math.sin(t*2.7)+talk*Math.sin(t*5)*.65;
  const leftShoulder=12+presenting*24+ending*13+emphasis*9;
  const rightShoulder=12+pointing*42+presenting*22+ending*12+pinch*34+emphasis*17;
  const leftElbow=-15-presenting*67-ending*55-emphasis*25;
  const rightElbow=-15-pointing*65-presenting*67-ending*50-pinch*56-emphasis*20;
  const segments=data.segments || [];
  const line=segments.find(s=>t>=s.start&&t<s.end)?.text || '';
  const words=line.trim().split(/\s+/); let lines=[''];
  for(const word of words){const j=lines.length-1;if((lines[j]+' '+word).trim().length>35)lines.push(word);else lines[j]=(lines[j]+' '+word).trim();}
  const subtitle=lines.slice(0,3).map((s,i)=>`<text x="360" y="${1160+i*34}" text-anchor="middle" font-family="Arial,sans-serif" font-size="27" font-weight="700" fill="#fff">${esc(s)}</text>`).join('');
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280" viewBox="0 0 720 1280" font-family="Arial,sans-serif">
  <defs>
    <linearGradient id="bg" x2="0" y2="1"><stop stop-color="#f6f2e9"/><stop offset="1" stop-color="#dfe7e8"/></linearGradient>
    <linearGradient id="skin" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffd6a8"/><stop offset=".6" stop-color="#efad7f"/><stop offset="1" stop-color="#d88d67"/></linearGradient>
    <linearGradient id="shirt" x2="1" y2=".5"><stop stop-color="#233049"/><stop offset=".45" stop-color="#3a4d71"/><stop offset="1" stop-color="#19253a"/></linearGradient>
    <linearGradient id="hair" x2=".8" y2="1"><stop stop-color="#75432d"/><stop offset=".5" stop-color="#38241d"/><stop offset="1" stop-color="#181a21"/></linearGradient>
    <linearGradient id="glass" x2=".6" y2="1"><stop stop-color="#343942"/><stop offset="1" stop-color="#10141c"/></linearGradient>
  </defs>
  <rect width="720" height="1280" fill="url(#bg)"/>
  <circle cx="680" cy="850" r="280" fill="#cddcdd" opacity=".5"/>
  <text x="46" y="56" font-family="Arial,sans-serif" font-size="17" font-weight="700" letter-spacing="3" fill="#344963">ROVOR DIGITAL</text>
  ${renderScene(t,data)}
  <g data-bone="root" transform="translate(360 ${bob}) rotate(${lean} 0 1050)">
    <path d="M-85 1027 L-93 1280 -12 1280 0 1099 20 1280 99 1280 77 1027Z" fill="#21232a" stroke="#121821" stroke-width="4"/>
    ${arm('left',leftShoulder,leftElbow,false)}
    ${arm('right',rightShoulder,rightElbow,pointing>.5)}
    <g data-bone="torso">
      <path d="M-91 718 Q-49 694 -26 692 L31 691 Q63 700 93 720 L77 1018 Q0 1041 -80 1018Z" fill="url(#shirt)" stroke="#121b2b" stroke-width="4"/>
      <path d="M-54 782 L-68 946 -49 970 M54 787 L63 957 43 981 M-61 989 Q0 1008 64 988" fill="none" stroke="#16253c" stroke-width="5"/>
      <path d="M-83 731 Q-48 748 -24 760 M82 731 Q49 743 29 761" stroke="#536280" stroke-width="3" fill="none"/>
      <path d="M-26 654 L-29 709 0 748 32 708 28 651Z" fill="url(#skin)" stroke="#3b2b2b" stroke-width="3"/>
      <path d="M-29 693 L-54 711 -24 770 0 739 -11 716Z M30 693 L51 714 27 766 0 739 14 716Z" fill="#1f2d44" stroke="#101d31" stroke-width="3"/>
      <path d="M-15 740 L12 740 18 760 5 778 -15 765Z" fill="#22242b" stroke="#11151e" stroke-width="3"/>
      <path d="M-7 772 L7 775 25 981 -2 1010 -26 982Z" fill="#25262d" stroke="#121721" stroke-width="3"/>
      <path d="M-7 789 L-12 970 0 990" fill="none" stroke="#424148" stroke-width="3"/>
      <path d="M-81 1013 Q0 1030 80 1013 L79 1044 Q0 1057 -82 1044Z" fill="#131821" stroke="#0d121b" stroke-width="3"/>
      <rect x="-18" y="1023" width="34" height="27" rx="3" fill="#697078"/><rect x="-12" y="1029" width="22" height="15" fill="#1c2029"/>
    </g>
    <g data-bone="head" transform="rotate(${head} 0 696)">
      <ellipse cx="-77" cy="601" rx="17" ry="30" fill="url(#skin)" stroke="#4d332c" stroke-width="3"/>
      <path d="M-70 529 Q-36 495 28 508 Q82 519 80 574 L67 638 Q55 674 19 693 Q-7 705 -35 679 L-65 642Z" fill="url(#skin)" stroke="#352a2b" stroke-width="3.5"/>
      <path d="M-63 616 Q-48 646 -26 652 M46 626 Q56 612 62 602" fill="none" stroke="#c88462" stroke-width="3"/>
      <path d="M4 582 L-1 622 Q9 632 20 622" fill="none" stroke="#b36d50" stroke-width="3" stroke-linecap="round"/>
      <path d="M-31 662 Q-8 680 12 681 Q33 676 53 657 L48 678 18 696 -3 698 -28 681Z" fill="#4b3025" opacity=".95"/>
      <path d="M-29 660 L-26 675 M-19 670 L-15 684 M-7 675 L-5 691 M6 679 L7 695 M22 675 L23 689 M34 670 L34 682" stroke="#8f6042" stroke-width="2"/>
      <g data-channel="mouth" transform="translate(9 649)">${mouth(cue)}</g>
      <path d="M-78 576 L-88 548 -85 522 -95 505 -77 509 -80 489 -58 495 -62 478 -37 488 -32 462 -13 478 1 453 10 479 33 461 30 482 55 470 48 490 77 487 65 507 89 507 78 527 92 539 78 552 71 577 56 565 56 542 Q37 531 26 519 Q6 546 -21 540 L-10 529 Q-44 555 -63 546 L-66 577Z" fill="url(#hair)" stroke="#211d20" stroke-width="4" stroke-linejoin="round"/>
      <path d="M-73 520 Q-27 524 -5 482 M-63 535 Q-22 531 4 499 M8 515 Q33 504 41 484 M34 522 Q56 526 69 514 M-37 500 L-27 482 M-9 518 Q14 504 14 484" fill="none" stroke="#8c5738" stroke-width="4" stroke-linecap="round" opacity=".8"/>
      <path d="M-76 576 L-59 569 M-61 564 Q-37 550 -12 562 M17 561 Q40 550 65 564" stroke="#211d22" stroke-width="7" fill="none"/>
      <g data-part="sunglasses" transform="rotate(5 0 585)">
        <path d="M-63 563 Q-37 555 -9 564 L-13 600 Q-34 612 -58 600Z" fill="url(#glass)" stroke="#11151d" stroke-width="7"/>
        <path d="M12 564 Q38 555 66 565 L61 601 Q38 612 17 600Z" fill="url(#glass)" stroke="#11151d" stroke-width="7"/>
        <path d="M-9 572 Q1 566 12 572 M-65 568 L-79 581" stroke="#11151d" stroke-width="6" fill="none"/>
        <path d="M-55 567 L-49 589 M22 567 L28 584" stroke="#5e6570" stroke-width="3" opacity=".6"/>
      </g>
    </g>
  </g>
  <rect x="36" y="1119" width="648" height="${lines.length>2?123:95}" rx="18" fill="#14243a" opacity=".96"/>
  ${subtitle}
  <rect x="46" y="1252" width="628" height="4" rx="2" fill="#c0ced3"/>
  <rect x="46" y="1252" width="${628*clamp(t/data.duration,0,1)}" height="4" rx="2" fill="#cc9a60"/>
  </svg>`;
  return svg;
}
module.exports={render,mouth};
