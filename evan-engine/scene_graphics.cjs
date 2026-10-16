// Offline SVG visual vocabulary. Every element is custom vector artwork.
const {cleanTitle}=(()=>({cleanTitle:s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c])).slice(0,52)}))();
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function browser(t, favicon=false) {
  const switchOn=favicon?clamp((t-0.6)/.7,0,1):0;
  return `<rect x="0" y="3" width="624" height="247" rx="21" fill="#162940" opacity=".14"/>
  <rect width="624" height="242" rx="19" fill="#fff" stroke="#b8c7d3" stroke-width="3"/>
  <path d="M19 0H604Q624 0 624 20V58H0V20Q0 0 19 0" fill="#e9eef3"/>
  <circle cx="24" cy="24" r="5" fill="#dc8d87"/><circle cx="43" cy="24" r="5" fill="#ebc579"/><circle cx="61" cy="24" r="5" fill="#82bea6"/>
  <rect x="80" y="8" width="232" height="49" rx="11" fill="#fff"/>
  <g transform="translate(105 34)">
   <g opacity="${1-switchOn}"><circle r="9" stroke="#718297" stroke-width="2" fill="none"/><ellipse rx="3.7" ry="9" stroke="#718297" stroke-width="1.5" fill="none"/><path d="M-9 0H9" stroke="#718297" stroke-width="1.5"/></g>
   <g opacity="${switchOn}"><rect x="-12" y="-12" width="24" height="24" rx="5" fill="#223d60"/><text x="0" y="7" text-anchor="middle" font-size="19" font-weight="900" fill="white">R</text></g>
   <circle r="${19+2*Math.sin(t*3)}" fill="none" stroke="#d8a35f" stroke-width="3" opacity=".82"/>
  </g>
  <text x="127" y="40" font-family="Arial,sans-serif" font-size="16" font-weight="600" fill="#405266">Your website</text>
  <rect x="20" y="75" width="584" height="29" rx="8" fill="#f0f4f7"/>
  <text x="36" y="95" font-size="13" fill="#748697">https://yourbrand.com</text>
  <rect x="24" y="122" width="113" height="90" rx="10" fill="#dce8ed"/>
  <circle cx="81" cy="166" r="24" fill="#b8cfda"/><path d="M61 188L94 145 110 188Z" fill="#7fa7b6"/>
  <rect x="159" y="128" width="273" height="15" rx="7" fill="#aabfcf"/>
  <rect x="159" y="161" width="408" height="9" rx="4" fill="#e0e8ee"/>
  <rect x="159" y="184" width="361" height="9" rx="4" fill="#e0e8ee"/>
  <rect x="159" y="203" width="123" height="13" rx="5" fill="#d4a66b"/>`;
}
function favicon(t){
  const scale=1+.07*Math.sin(t*3);
  return `<rect x="0" y="0" width="624" height="244" rx="20" fill="#fff" stroke="#c0cbd5" stroke-width="3"/>
  <text x="30" y="35" font-size="18" font-weight="700" fill="#344860">BEFORE</text>
  <text x="341" y="35" font-size="18" font-weight="700" fill="#344860">AFTER</text>
  <rect x="26" y="54" width="269" height="148" rx="15" fill="#eef2f6"/>
  <rect x="325" y="54" width="273" height="148" rx="15" fill="#e5edf4"/>
  <g transform="translate(161 128)"><circle r="41" stroke="#84909b" stroke-width="6" fill="none"/><ellipse rx="19" ry="41" stroke="#84909b" stroke-width="4" fill="none"/><path d="M-39 0H39M-32 -21H32M-32 21H32" stroke="#84909b" stroke-width="3"/></g>
  <g transform="translate(460 128) scale(${scale})"><rect x="-50" y="-50" width="100" height="100" rx="23" fill="#1e3c60"/><path d="M-22 -28V28M-23 -28H8Q33 -28 33 -9Q33 11 7 11H-23M8 11L32 30" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></g>
  <path d="M295 129H325" stroke="#cc9b5c" stroke-width="7"/><path d="M317 116L335 129 317 142" fill="none" stroke="#cc9b5c" stroke-width="6"/>
  <text x="312" y="230" text-anchor="middle" font-size="15" fill="#506278">Your identity, even in a tiny tab.</text>`;
}
function brand(t){
  return `<rect x="0" y="0" width="624" height="244" rx="22" fill="#fff" stroke="#c3cfd8" stroke-width="3"/>
  <rect x="31" y="26" width="270" height="185" rx="16" fill="#203a57"/>
  <g transform="translate(165 105) rotate(${1.5*Math.sin(t*2)})"><rect x="-38" y="-40" width="76" height="76" rx="16" fill="#dbac72"/><text text-anchor="middle" y="20" font-size="59" font-weight="900" fill="#1d344c">R</text></g>
  <text x="165" y="188" text-anchor="middle" font-size="22" font-weight="800" letter-spacing="2" fill="#fff">ROVOR</text>
  <text x="340" y="60" font-size="23" font-weight="800" fill="#263a56">BUILD A BRAND</text>
  <rect x="338" y="84" width="242" height="14" rx="7" fill="#b2c6d4"/>
  <rect x="338" y="110" width="211" height="11" rx="6" fill="#dfe8ec"/>
  <rect x="338" y="134" width="170" height="11" rx="6" fill="#dfe8ec"/>
  <circle cx="360" cy="182" r="20" fill="#1f3b59"/><circle cx="409" cy="182" r="20" fill="#d3a36c"/><circle cx="458" cy="182" r="20" fill="#b5cbd2"/>
  <text x="340" y="229" font-size="15" fill="#5c6f83">Consistent across every screen.</text>`;
}
function social(t){
  return `<rect x="0" y="0" width="624" height="244" rx="22" fill="#fff" stroke="#bfcbd6" stroke-width="3"/>
  <g transform="translate(35 19)">
  <rect width="191" height="205" rx="19" fill="#233955"/>
  <rect x="10" y="14" width="171" height="143" rx="12" fill="#cbdce3"/>
  <rect x="28" y="34" width="137" height="82" rx="10" fill="#84a6b5"/><circle cx="98" cy="75" r="22" fill="#cfaa77"/>
  <path d="M90 59L90 91 113 76Z" fill="#fff"/>
  <circle cx="23" cy="176" r="8" fill="#d7a66f"/><rect x="40" y="169" width="112" height="12" rx="6" fill="#e5ebf0"/>
  </g>
  <g transform="translate(249 25)"><rect width="339" height="38" rx="12" fill="#edf2f4"/><text x="19" y="26" font-size="18" fill="#38516b" font-weight="700">Your content</text>
  <rect y="58" width="103" height="109" rx="13" fill="#d8e3e9"/><rect x="116" y="58" width="103" height="109" rx="13" fill="#c9d8e2"/><rect x="232" y="58" width="103" height="109" rx="13" fill="#d9d9db"/>
  <path d="M37 93L37 137 78 115Z M151 93L151 137 191 115Z M266 93L266 137 304 115Z" fill="#fff"/>
  <rect x="0" y="184" width="267" height="10" rx="5" fill="#d7e1e8"/></g>`;
}
function store(t){
  return `<rect width="624" height="244" rx="22" fill="#fff" stroke="#bfccd5" stroke-width="3"/>
  <rect x="30" y="29" width="175" height="183" rx="14" fill="#e0e7eb"/>
  <path d="M90 61L110 42 132 61 155 74 139 127 148 177 69 177 77 127 61 74Z" fill="#304962" stroke="#23344a" stroke-width="3"/>
  <text x="226" y="51" font-size="23" font-weight="800" fill="#233a56">YOUR ONLINE STORE</text>
  <rect x="226" y="73" width="316" height="13" rx="6" fill="#bed0db"/>
  <rect x="226" y="105" width="265" height="10" rx="5" fill="#e1e8ed"/>
  <rect x="226" y="129" width="296" height="10" rx="5" fill="#e1e8ed"/>
  <rect x="226" y="166" width="201" height="44" rx="10" fill="#d5a16a"/>
  <text x="326" y="195" text-anchor="middle" font-size="17" font-weight="800" fill="#273b4c">CHECKOUT</text>
  <g transform="translate(${485+5*Math.sin(t*2)} 182)"><path d="M0 -18H10L18 13H53L65 -9H16" stroke="#2a405b" stroke-width="5" stroke-linejoin="round" stroke-linecap="round" fill="none"/><circle cx="25" cy="23" r="5" fill="#2a405b"/><circle cx="50" cy="23" r="5" fill="#2a405b"/></g>`;
}
function search(t){
  return `<rect width="624" height="244" rx="20" fill="#fff" stroke="#bfccd5" stroke-width="3"/>
  <rect x="28" y="23" width="565" height="55" rx="21" fill="#f3f6f8" stroke="#cad6de" stroke-width="2"/>
  <circle cx="58" cy="50" r="12" fill="none" stroke="#5d748a" stroke-width="4"/><path d="M67 60L81 73" stroke="#5d748a" stroke-width="4"/>
  <text x="103" y="58" font-size="20" fill="#435c73">Your business</text>
  <rect x="37" y="102" width="486" height="18" rx="8" fill="#b2cbd8"/>
  <rect x="37" y="136" width="394" height="11" rx="5" fill="#d8e5eb"/>
  <rect x="37" y="157" width="457" height="11" rx="5" fill="#d8e5eb"/>
  <rect x="37" y="190" width="206" height="19" rx="7" fill="#d8a773"/>
  <circle cx="560" cy="181" r="${25+Math.sin(t*3)*2}" fill="#e4edf3"/>
  <path d="M547 181L557 192 576 170" fill="none" stroke="#3b6980" stroke-width="5" stroke-linecap="round"/>`;
}
function contact(t){
  return `<rect width="624" height="244" rx="20" fill="#fff" stroke="#bfccd5" stroke-width="3"/>
  <g transform="translate(30 26)"><rect width="354" height="196" rx="14" fill="#f3f6f9"/>
  <text x="21" y="33" font-size="21" font-weight="800" fill="#283e58">LET'S CONNECT</text>
  <rect x="20" y="50" width="314" height="37" rx="8" fill="#fff" stroke="#c8d5dd"/>
  <rect x="20" y="100" width="314" height="37" rx="8" fill="#fff" stroke="#c8d5dd"/>
  <rect x="20" y="153" width="164" height="31" rx="8" fill="#cf9e69"/></g>
  <g transform="translate(426 63) rotate(${2*Math.sin(t*2)})"><rect width="158" height="114" rx="15" fill="#23405f"/><path d="M6 19L79 77 152 19" stroke="#d6e5eb" stroke-width="5" fill="none"/><path d="M6 97L61 55M152 97L97 55" stroke="#d6e5eb" stroke-width="4"/></g>`;
}
function endcard(t){
  const s=1+.025*Math.sin(t*2);
  return `<rect width="624" height="244" rx="21" fill="#213b57"/>
  <g transform="translate(312 105) scale(${s})"><circle r="65" fill="#2e4e6d"/><circle r="50" fill="none" stroke="#cd9d67" stroke-width="5"/><path d="M-15 -33V28M-15 -33H15Q40 -33 40 -8Q40 15 8 15H-15M9 15L33 35" fill="none" stroke="#fff" stroke-width="11" stroke-linejoin="round"/></g>
  <text x="312" y="208" font-size="28" letter-spacing="5" text-anchor="middle" fill="#fff" font-weight="900">ROVOR DIGITAL</text>`;
}
function topic(t,title){
  return `<rect width="624" height="244" rx="22" fill="#fff" stroke="#bfccd5" stroke-width="3"/>
  <rect x="25" y="27" width="574" height="60" rx="13" fill="#e4edf1"/>
  <circle cx="61" cy="57" r="15" fill="#d3a16a"/>
  <text x="96" y="67" font-size="23" font-weight="800" fill="#253d57">${cleanTitle(title || 'HERE’S THE IDEA')}</text>
  <g transform="translate(47 115)"><circle cx="12" cy="12" r="12" fill="#caa06f"/>
  <path d="M7 12L11 16 19 7" stroke="#fff" stroke-width="3" fill="none"/>
  <rect x="41" y="2" width="352" height="16" rx="7" fill="#adc3d1"/>
  <circle cx="12" cy="51" r="12" fill="#caa06f"/>
  <path d="M7 51L11 55 19 46" stroke="#fff" stroke-width="3" fill="none"/>
  <rect x="41" y="41" width="430" height="16" rx="7" fill="#d7e1e8"/></g>`;
}
function graphic(kind,t,title) {
  if (kind==='browser') return browser(t);
  if (kind==='favicon') return favicon(t);
  if (kind==='brand') return brand(t);
  if (kind==='social') return social(t);
  if (kind==='store') return store(t);
  if (kind==='search') return search(t);
  if (kind==='contact') return contact(t);
  if (kind==='endcard') return endcard(t);
  return topic(t,title);
}
const HEADLINES={browser:'YOUR WEBSITE',favicon:'A TINY ICON. A REAL DIFFERENCE.',brand:'MAKE YOUR BRAND RECOGNIZABLE',social:'CONTENT PEOPLE WANT TO WATCH',store:'MAKE CHECKOUT SIMPLE',search:'HELP PEOPLE FIND YOU',contact:'TURN INTEREST INTO INQUIRIES',endcard:'GO BEYOND YOUR CURRENT REACH.',topic:'A MINUTE WITH EVAN'};
function renderScene(t,data){
  const scenes=Array.isArray(data.scenePlan)&&data.scenePlan.length?data.scenePlan:[{start:0,end:data.duration,kind:'topic',title:'A minute with Evan'}];
  return scenes.filter(s=>t>=s.start-.24&&t<=s.end+.24).map((s,i)=>{
    const incoming=clamp((t-s.start+.20)/.40,0,1);
    const outgoing=clamp((s.end-t+.20)/.40,0,1);
    const opacity=Math.min(incoming,outgoing);
    const shift=(1-incoming)*12;
    const kind=s.kind||'topic';
    return `<g opacity="${opacity.toFixed(3)}" transform="translate(0 ${shift.toFixed(2)})">
    <text x="46" y="109" font-size="${(HEADLINES[kind]||HEADLINES.topic).length>34?28:33}" font-weight="900" fill="#213650" font-family="Arial,sans-serif">${HEADLINES[kind]||HEADLINES.topic}</text>
    <g transform="translate(48 152)">${graphic(kind,Math.max(0,t-s.start),s.title)}</g>
    </g>`;
  }).join('');
}
module.exports={renderScene};
