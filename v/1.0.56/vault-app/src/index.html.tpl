<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>PHP2Shell evidence vault</title>
<style>
/* Every colour is a token; light and dark from the same names. No external resources. */
:root{
  color-scheme:light;
  --bg:#f7f6f2; --panel:#ffffff; --panel2:#fbfaf7; --fg:#1b1b1a; --head:#111; --dim:#5e5d58; --mute:#898781;
  --line:#e2e0d8; --line2:#cfccc2; --hover:rgba(11,11,11,.045); --sel:rgba(31,94,155,.10);
  --accent:#1f5e9b; --accent-dk:#17477a; --warm:#b4461c; --shadow:0 10px 30px rgba(20,20,10,.14);
  --good:#0ca30c; --warning:#fab219; --serious:#ec835a; --critical:#d03b3b; --info:#2a78d6; --neutral:#898781;
  --good-ink:#1e5c2c; --good-bg:#e3f1e6; --warn-ink:#7a4d06; --warn-bg:#fbefd6; --ser-ink:#8a3a14; --ser-bg:#fbe6db;
  --crit-ink:#8a2416; --crit-bg:#f9e2de; --info-ink:#27446d; --info-bg:#e8eef7; --mute-ink:#444; --mute-bg:#ececea;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#6250d6; --s8:#e34948;
  --bar:#2a78d6; --grid:#e1e0d9; --axis:#c3c2b7;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; --serif:Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  color-scheme:dark;
  --bg:#141413; --panel:#1d1d1b; --panel2:#191918; --fg:#e8e6df; --head:#f3f1ea; --dim:#a3a199; --mute:#898781;
  --line:#2d2d2a; --line2:#43433e; --hover:rgba(255,255,255,.05); --sel:rgba(127,179,230,.14);
  --accent:#7fb3e6; --accent-dk:#a9cdf0; --warm:#f09a72; --shadow:0 10px 30px rgba(0,0,0,.5);
  --good-ink:#9fdcae; --good-bg:#1d3324; --warn-ink:#f2c979; --warn-bg:#3d2e12; --ser-ink:#f5b99a; --ser-bg:#40261a;
  --crit-ink:#f5a79a; --crit-bg:#43201b; --info-ink:#b7cdf0; --info-bg:#1f2b40; --mute-ink:#cfcdc5; --mute-bg:#2a2a28;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  --bar:#3987e5; --grid:#2c2c2a; --axis:#383835;
}}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#141413; --panel:#1d1d1b; --panel2:#191918; --fg:#e8e6df; --head:#f3f1ea; --dim:#a3a199; --mute:#898781;
  --line:#2d2d2a; --line2:#43433e; --hover:rgba(255,255,255,.05); --sel:rgba(127,179,230,.14);
  --accent:#7fb3e6; --accent-dk:#a9cdf0; --warm:#f09a72; --shadow:0 10px 30px rgba(0,0,0,.5);
  --good-ink:#9fdcae; --good-bg:#1d3324; --warn-ink:#f2c979; --warn-bg:#3d2e12; --ser-ink:#f5b99a; --ser-bg:#40261a;
  --crit-ink:#f5a79a; --crit-bg:#43201b; --info-ink:#b7cdf0; --info-bg:#1f2b40; --mute-ink:#cfcdc5; --mute-bg:#2a2a28;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  --bar:#3987e5; --grid:#2c2c2a; --axis:#383835;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);font-size:15px;line-height:1.5;-webkit-text-size-adjust:100%}
button{font:inherit;color:inherit}
a{color:var(--accent)} a:hover{color:var(--accent-dk)}
code,.mono{font-family:var(--mono);font-size:.86em}
svg.i{width:16px;height:16px;flex:none;vertical-align:-3px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}

/* shell */
.app{display:grid;grid-template-columns:220px 1fr;grid-template-rows:56px 1fr;height:100vh;height:100dvh}
.top{grid-column:1/-1;display:flex;align-items:center;gap:12px;padding:0 16px;background:var(--panel);border-bottom:1px solid var(--line);position:relative;z-index:30}
.brand{display:flex;align-items:center;gap:10px;min-width:0;cursor:pointer;background:none;border:0;padding:0;text-align:left}
.brand .mark{width:30px;height:30px;border-radius:8px;background:var(--head);color:var(--bg);display:grid;place-items:center;flex:none}
.brand .mark svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2}
.brand b{font-family:var(--serif);font-size:1.12rem;color:var(--head);white-space:nowrap}
.brand span{font-size:.78rem;color:var(--dim);white-space:nowrap}
.brand .t{display:flex;flex-direction:column;line-height:1.15;min-width:0}
.search{flex:1;max-width:560px;margin-left:auto;position:relative}
.search input{width:100%;height:36px;border-radius:9px;border:1px solid var(--line2);background:var(--panel2);padding:0 12px 0 34px;font:inherit;color:var(--fg)}
.search input:focus{outline:2px solid var(--accent);outline-offset:-1px;background:var(--panel)}
.search>svg{position:absolute;left:11px;top:10px;color:var(--mute)}
.search kbd{position:absolute;right:9px;top:8px;font-family:var(--mono);font-size:.7rem;color:var(--mute);border:1px solid var(--line2);border-radius:5px;padding:0 5px}
.chipbtn{display:inline-flex;align-items:center;gap:6px;height:30px;border:1px solid var(--line2);background:var(--panel);border-radius:999px;padding:0 10px;font-size:.78rem;color:var(--dim);cursor:pointer;white-space:nowrap}
.chipbtn:hover{background:var(--hover);color:var(--fg)}
.chipbtn.ver{font-family:var(--mono)}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}
.live .dot{background:var(--good)} .snap .dot{background:var(--warning)}
.iconbtn{width:34px;height:34px;display:grid;place-items:center;border:1px solid var(--line2);border-radius:9px;background:var(--panel);cursor:pointer;color:var(--dim)}
.iconbtn:hover{background:var(--hover);color:var(--fg)}

.side{background:var(--panel2);border-right:1px solid var(--line);padding:12px 10px;overflow:auto;display:flex;flex-direction:column;gap:2px}
.nav{display:flex;align-items:center;gap:10px;width:100%;border:0;background:none;padding:8px 10px;border-radius:8px;cursor:pointer;color:var(--fg);text-align:left;font-size:.92rem}
.nav:hover{background:var(--hover)}
.nav.on{background:var(--sel);color:var(--head);font-weight:600}
.nav .n{margin-left:auto;font-size:.74rem;color:var(--mute);font-variant-numeric:tabular-nums;font-weight:400}
.side .sep{height:1px;background:var(--line);margin:10px 6px}
.side .foot{margin-top:auto;font-size:.72rem;color:var(--mute);padding:10px 8px 2px;line-height:1.45}
.side .foot b{color:var(--dim);font-weight:600}

main{overflow:auto;position:relative;scroll-behavior:smooth}
.wrap{max-width:1240px;margin:0 auto;padding:22px 24px 64px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(1.55rem,3vw,2.25rem);line-height:1.15;margin:.2rem 0 .6rem;color:var(--head);letter-spacing:-.01em}
h2{font-size:1.05rem;margin:0 0 .7rem;color:var(--head)}
h3{font-size:.95rem;margin:1rem 0 .4rem;color:var(--head)}
.kicker{font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--dim);margin:0}
.lead{font-size:1.02rem;max-width:78ch;color:var(--fg);margin:.3rem 0 0}
.muted{color:var(--dim)} .small{font-size:.8rem} .tiny{font-size:.72rem}
.vh{display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.vh .grow{flex:1;min-width:260px}

/* cards & panels */
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.grid{display:grid;gap:14px}
.g-tiles{grid-template-columns:repeat(auto-fill,minmax(170px,1fr))}
.g-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.g-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;cursor:pointer;text-align:left;display:flex;flex-direction:column;justify-content:flex-start;width:100%}
.tile:hover{border-color:var(--line2);background:var(--panel2)}
.tile .v{font-size:1.9rem;font-weight:650;color:var(--head);line-height:1.1;margin:.15rem 0}
.tile .l{font-size:.78rem;color:var(--dim);text-transform:uppercase;letter-spacing:.06em}
.tile .s{font-size:.78rem;color:var(--dim)}
.sect{margin-top:22px}
.sect-h{display:flex;align-items:baseline;gap:10px;margin-bottom:10px}
.sect-h h2{margin:0}
.sect-h .more{margin-left:auto;font-size:.8rem;background:none;border:0;color:var(--accent);cursor:pointer;padding:0}

/* pills */
.pill{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:1px 8px;font-size:.72rem;font-weight:600;white-space:nowrap;line-height:1.6;border:1px solid transparent}
.pill svg.i{width:12px;height:12px;vertical-align:0}
.p-good{background:var(--good-bg);color:var(--good-ink)} .p-warn{background:var(--warn-bg);color:var(--warn-ink)}
.p-ser{background:var(--ser-bg);color:var(--ser-ink)} .p-crit{background:var(--crit-bg);color:var(--crit-ink)}
.p-info{background:var(--info-bg);color:var(--info-ink)} .p-mute{background:var(--mute-bg);color:var(--mute-ink)}
.p-line{border-color:var(--line2);color:var(--dim);font-weight:500}
.p-kind{background:var(--mute-bg);color:var(--mute-ink);font-weight:500}
.p-prim{background:var(--head);color:var(--bg)}

/* filters */
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 14px}
.fsearch{position:relative;flex:1 1 260px;max-width:420px}
.fsearch input{width:100%;height:34px;border-radius:8px;border:1px solid var(--line2);background:var(--panel);padding:0 10px 0 32px;font:inherit;color:var(--fg)}
.fsearch svg{position:absolute;left:10px;top:9px;color:var(--mute)}
.facets{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.frow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.frow .fl{font-size:.72rem;color:var(--mute);text-transform:uppercase;letter-spacing:.06em;width:74px;flex:none}
.chip{display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 10px;border:1px solid var(--line2);border-radius:999px;background:var(--panel);cursor:pointer;font-size:.8rem;color:var(--fg);white-space:nowrap}
.chip:hover{background:var(--hover)}
.chip.on{background:var(--head);border-color:var(--head);color:var(--bg)}
.chip .c{font-size:.72rem;color:var(--mute);font-variant-numeric:tabular-nums}
.chip.on .c{color:inherit;opacity:.75}
.seg{display:inline-flex;border:1px solid var(--line2);border-radius:8px;overflow:hidden}
.seg button{border:0;background:var(--panel);padding:6px 10px;font-size:.8rem;cursor:pointer;color:var(--dim);display:flex;align-items:center;gap:6px}
.seg button+button{border-left:1px solid var(--line2)}
.seg button.on{background:var(--sel);color:var(--head);font-weight:600}
select.sel{height:32px;border-radius:8px;border:1px solid var(--line2);background:var(--panel);color:var(--fg);font:inherit;font-size:.82rem;padding:0 8px}
.count{font-size:.8rem;color:var(--dim);margin-left:auto}
.empty{padding:40px 16px;text-align:center;color:var(--dim);border:1px dashed var(--line2);border-radius:12px}
.clear{background:none;border:0;color:var(--accent);cursor:pointer;font-size:.8rem;padding:0}

/* source cards */
.g-cards{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;text-align:left;padding:0;width:100%}
.card:hover{border-color:var(--line2);box-shadow:var(--shadow)}
.thumb{position:relative;aspect-ratio:16/10;background:var(--mute-bg);overflow:hidden;border-bottom:1px solid var(--line)}
.thumb img{width:100%;height:100%;object-fit:cover;object-position:top;display:block;opacity:0;transition:opacity .35s}
.thumb img.ok{opacity:1}
.thumb .ph{position:absolute;inset:0;display:grid;place-items:center;color:var(--mute);font-size:.78rem;text-align:center;padding:12px}
.thumb .ph svg{width:26px;height:26px;display:block;margin:0 auto 6px}
.thumb .ov{position:absolute;left:8px;top:8px;display:flex;gap:5px}
.thumb .ncap{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.62);color:#fff;font-size:.7rem;border-radius:6px;padding:1px 6px}
.card .b{padding:10px 12px 12px;display:flex;flex-direction:column;gap:4px;flex:1}
.card .pub{font-size:.74rem;color:var(--dim);display:flex;gap:6px;align-items:center;min-width:0}
.card .pub span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card .ti{font-weight:600;font-size:.9rem;color:var(--head);line-height:1.3;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card .ft{margin-top:auto;padding-top:6px;display:flex;gap:10px;font-size:.72rem;color:var(--mute);flex-wrap:wrap}

/* table */
.tbl{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:.84rem}
.tbl th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);font-weight:600;padding:9px 10px;border-bottom:1px solid var(--line);background:var(--panel2);position:sticky;top:0}
.tbl td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.tbl tr:last-child td{border-bottom:0}
.tbl tbody tr{cursor:pointer}
.tbl tbody tr:hover{background:var(--hover)}
.tbl .num{text-align:right;font-variant-numeric:tabular-nums}
.tscroll{overflow-x:auto;border-radius:12px}

/* lists */
.list{display:flex;flex-direction:column;gap:10px}
.claim{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 15px;display:flex;flex-direction:column;gap:7px}
.claim .top1{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.claim .txt{font-size:.97rem;color:var(--head);line-height:1.45}
.claim .by{font-size:.8rem;color:var(--dim)}
.claim .note{font-size:.84rem;color:var(--fg);border-left:3px solid var(--warm);padding:2px 0 2px 10px;background:none}
.claim .meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:.74rem;color:var(--mute)}
.claim.flash,.ev.flash{animation:flash 1.8s ease}
@keyframes flash{0%,40%{box-shadow:0 0 0 3px var(--accent)}100%{box-shadow:0 0 0 0 transparent}}
.srcs{display:flex;gap:6px;flex-wrap:wrap}
.sc{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line2);background:var(--panel2);border-radius:7px;padding:2px 8px;font-size:.76rem;cursor:pointer;color:var(--fg);max-width:100%}
.sc:hover{border-color:var(--accent);color:var(--accent)}
.sc span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:260px}
.sc.miss{border-style:dashed;color:var(--crit-ink);cursor:help}
.sc .st{font-size:.7rem}
.grp-h{display:flex;align-items:center;gap:8px;margin:20px 0 8px;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:var(--dim)}
.grp-h:first-child{margin-top:0}
.grp-h .c{color:var(--mute)}
.grp-h::after{content:"";flex:1;height:1px;background:var(--line)}

/* timeline */
.tl{position:relative;padding-left:0}
.day{display:grid;grid-template-columns:120px 1fr;gap:0 18px;margin-bottom:6px}
.day .dl{position:sticky;top:0;align-self:start;padding-top:12px;font-weight:650;color:var(--head);font-size:.86rem}
.day .dl small{display:block;font-weight:400;color:var(--mute);font-size:.72rem}
.evs{border-left:2px solid var(--line);padding-left:18px}
.ev{position:relative;padding:10px 12px;margin:8px 0;background:var(--panel);border:1px solid var(--line);border-radius:10px}
.ev::before{content:"";position:absolute;left:-26px;top:16px;width:12px;height:12px;border-radius:50%;background:var(--pc,var(--neutral));border:2px solid var(--bg)}
.ev.inf{border-style:dashed}
.ev .when{font-family:var(--mono);font-size:.74rem;color:var(--dim)}
.ev .what{color:var(--head);margin:3px 0 6px;font-size:.93rem}
.ev .meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:.74rem;color:var(--mute);margin-bottom:6px}
.ev .note{font-size:.82rem;color:var(--dim);margin:0 0 6px}
.ph-dot{width:9px;height:9px;border-radius:50%;display:inline-block;background:var(--pc,var(--neutral))}

/* wall */
.g-wall{grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.shot{position:relative;border-radius:10px;overflow:hidden;cursor:pointer;border:1px solid var(--line);background:var(--mute-bg);padding:0;display:block;width:100%;text-align:left}
.shot .thumb{border:0}
.shot .cap{position:absolute;left:0;right:0;bottom:0;padding:22px 9px 7px;background:linear-gradient(transparent,rgba(0,0,0,.78));color:#fff;font-size:.72rem;line-height:1.3}
.shot .cap b{display:block;font-size:.76rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.shot:hover{box-shadow:var(--shadow)}
.hour-h{font-family:var(--mono);font-size:.78rem;color:var(--dim);margin:18px 0 8px;display:flex;gap:8px;align-items:center}
.hour-h::after{content:"";flex:1;height:1px;background:var(--line)}

/* charts */
.chart{position:relative}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
.chart .tick{font-size:10px;fill:var(--mute);font-family:var(--sans)}
.chart .gl{stroke:var(--grid);stroke-width:1}
.chart .ax{stroke:var(--axis);stroke-width:1}
.chart .bar{fill:var(--bar)}
.chart .hit{fill:transparent;cursor:pointer}
.chart .hit:hover+.bar,.chart g.b:hover .bar{opacity:.8}
.tip{position:absolute;pointer-events:none;background:var(--head);color:var(--bg);font-size:.74rem;border-radius:7px;padding:5px 8px;white-space:nowrap;transform:translate(-50%,-110%);opacity:0;transition:opacity .1s;z-index:5}
.stack{display:flex;height:22px;border-radius:6px;overflow:hidden;gap:2px;background:var(--panel)}
.stack button{border:0;padding:0;cursor:pointer;min-width:6px}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:.8rem}
.legend button{background:none;border:0;padding:0;display:inline-flex;align-items:center;gap:6px;cursor:pointer;color:var(--fg)}
.legend b{font-variant-numeric:tabular-nums}
.hbar{display:grid;grid-template-columns:minmax(90px,140px) 1fr 36px;gap:8px;align-items:center;font-size:.82rem;padding:3px 0;cursor:pointer;background:none;border:0;width:100%;text-align:left;color:var(--fg)}
.hbar:hover .tr i{opacity:.8}
.hbar .tr{height:10px;background:var(--mute-bg);border-radius:0 4px 4px 0;overflow:hidden}
.hbar .tr i{display:block;height:100%;background:var(--bar);border-radius:0 4px 4px 0}
.hbar .nm{text-align:right;color:var(--dim);font-variant-numeric:tabular-nums}
.att li{margin:0 0 8px;font-size:.86rem;list-style:none}
.att{padding:0;margin:0}
.att .x{display:block;color:var(--dim);font-size:.78rem;margin-top:2px}
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.agents td{font-variant-numeric:tabular-nums}

/* drawer */
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.28);opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(680px,100vw);background:var(--bg);border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(102%);transition:transform .22s ease;z-index:41;display:flex;flex-direction:column}
.drawer.on{transform:none}
.dh{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
.dh .crumbs{font-size:.78rem;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.db{overflow:auto;padding:18px 20px 40px;flex:1}
.db h2.t{font-family:var(--serif);font-size:1.35rem;font-weight:600;line-height:1.25;margin:.4rem 0 .5rem}
.kv{display:grid;grid-template-columns:120px 1fr;gap:4px 12px;font-size:.84rem;margin:10px 0}
.kv dt{color:var(--mute)} .kv dd{margin:0;overflow-wrap:anywhere}
.caps{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.capc{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel);cursor:pointer;padding:0;text-align:left;width:100%}
.capc .m{padding:6px 8px;font-size:.72rem;color:var(--dim);font-family:var(--mono)}
.dsec{margin-top:22px}
.dsec>h3{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);margin:0 0 8px;display:flex;gap:8px;align-items:center}
.files{list-style:none;padding:0;margin:0;font-size:.82rem;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel)}
.files li{display:flex;gap:10px;padding:6px 10px;border-bottom:1px solid var(--line);align-items:center}
.files li:last-child{border-bottom:0}
.files li.dir{background:var(--panel2);font-family:var(--mono);font-size:.74rem;color:var(--dim)}
.files button{background:none;border:0;padding:0;color:var(--accent);cursor:pointer;font-family:var(--mono);font-size:.78rem;text-align:left;overflow-wrap:anywhere}
.files .sz{margin-left:auto;color:var(--mute);font-variant-numeric:tabular-nums;font-size:.74rem;white-space:nowrap}
.prov{font-family:var(--mono);font-size:.72rem;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;overflow-x:auto}
.prov table{border-collapse:collapse}
.prov td{padding:2px 10px 2px 0;vertical-align:top;white-space:nowrap}
.prov td:first-child{color:var(--mute)}

/* markdown */
.md{font-size:.92rem;line-height:1.6;overflow-wrap:anywhere}
.md h1,.md h2,.md h3,.md h4{font-family:var(--sans);color:var(--head);margin:1.1em 0 .4em;line-height:1.3}
.md h1{font-size:1.3rem} .md h2{font-size:1.1rem} .md h3{font-size:.98rem} .md h4{font-size:.9rem}
.md>:first-child{margin-top:0}
.db .md h1{font-size:1.05rem} .db .md h2{font-size:.98rem}
.md p{margin:.5em 0} .md ul,.md ol{padding-left:1.3em;margin:.4em 0} .md li{margin:.2em 0}
.md code{background:var(--mute-bg);padding:.05em .3em;border-radius:4px}
.md pre{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;font-size:.8rem}
.md pre code{background:none;padding:0}
.md blockquote{margin:.6em 0;padding:.1em .9em;border-left:3px solid var(--line2);color:var(--dim)}
.md table{border-collapse:collapse;font-size:.82rem;margin:.6em 0;display:block;overflow-x:auto}
.md th,.md td{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
.md th{background:var(--panel2)}
.md hr{border:0;border-top:1px solid var(--line);margin:1em 0}
.transcript p{margin:.2em 0 .7em}
.transcript .sp{font-size:.74rem;color:var(--mute);font-family:var(--mono);display:block;margin-top:.8em}

/* desk */
.desk{display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:start}
.docs{display:flex;flex-direction:column;gap:6px;position:sticky;top:0}
.doc{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:9px 11px;cursor:pointer;text-align:left;width:100%}
.doc:hover{border-color:var(--line2)}
.doc.on{border-color:var(--accent);background:var(--sel)}
.doc b{display:block;font-size:.86rem;color:var(--head)}
.doc span{font-size:.74rem;color:var(--dim)}
.reader{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 24px;min-height:300px}
.reader .md{max-width:78ch}

/* viewer */
.lb{position:fixed;inset:0;background:rgba(10,10,9,.92);z-index:60;display:none;grid-template-columns:1fr 320px;color:#eee}
.lb.on{display:grid}
.lb .stage{overflow:auto;display:flex;justify-content:center;padding:20px;position:relative}
.lb .stage img{max-width:min(1100px,100%);height:auto;display:block;background:#fff;box-shadow:0 10px 40px rgba(0,0,0,.6);border-radius:4px}
.lb .stage .loading{position:absolute;top:40%;left:0;right:0;text-align:center;color:#aaa;font-size:.85rem}
.lb .info{background:#161615;border-left:1px solid #2d2d2a;padding:16px;overflow:auto;display:flex;flex-direction:column;gap:10px}
.lb .info .pub{font-size:.78rem;color:#aaa}
.lb .info h3{font-family:var(--serif);font-size:1.1rem;color:#fff;margin:0;line-height:1.3;font-weight:600}
.lb .info .when{font-family:var(--mono);font-size:.78rem;color:#ccc}
.lb .info .cut{font-size:.74rem;color:#f2c979}
.lb .nav2{display:flex;gap:8px;align-items:center}
.lb .b2{border:1px solid #43433e;background:#1d1d1b;color:#eee;border-radius:8px;padding:7px 10px;cursor:pointer;font-size:.8rem;display:inline-flex;gap:6px;align-items:center;justify-content:center}
.lb .b2:hover{background:#2a2a28}
.lb .col{display:flex;flex-direction:column;gap:6px}
.lb .pos{font-size:.76rem;color:#aaa;margin-left:auto;font-variant-numeric:tabular-nums}
.lb .x{position:fixed;top:10px;right:332px;z-index:61}
.lb .x2{display:none}

/* text reader modal */
.tr-m{position:fixed;inset:0;z-index:70;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;padding:20px}
.tr-m.on{display:flex}
.tr-box{background:var(--bg);border:1px solid var(--line);border-radius:12px;width:min(980px,100%);height:min(86vh,100%);display:flex;flex-direction:column;box-shadow:var(--shadow)}
.tr-box .dh{border-radius:12px 12px 0 0}
.tr-box pre{margin:0;padding:16px 18px;overflow:auto;flex:1;font-family:var(--mono);font-size:.78rem;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere}
.tr-box .md{padding:16px 22px;overflow:auto;flex:1}

/* search dropdown */
.sres{position:absolute;top:42px;left:0;right:0;background:var(--panel);border:1px solid var(--line2);border-radius:12px;box-shadow:var(--shadow);max-height:70vh;overflow:auto;display:none;padding:6px}
.sres.on{display:block}
.sres .gh{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mute);padding:8px 10px 4px}
.sres .r{display:block;width:100%;text-align:left;background:none;border:0;padding:7px 10px;border-radius:8px;cursor:pointer}
.sres .r:hover,.sres .r.act{background:var(--sel)}
.sres .r b{display:block;font-size:.86rem;font-weight:600;color:var(--head);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sres .r span{display:block;font-size:.74rem;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sres .none{padding:14px;color:var(--dim);font-size:.85rem}
mark{background:rgba(250,178,25,.35);color:inherit;border-radius:2px;padding:0 1px}

.foot2{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:.78rem;color:var(--mute);display:flex;gap:12px;flex-wrap:wrap}
.foot2 svg{color:var(--dim)}
.boot{display:grid;place-items:center;height:60vh;color:var(--dim);font-size:.9rem}

.mtabs{display:none}
@media (max-width:980px){
  .g-3{grid-template-columns:1fr 1fr}
  .desk{grid-template-columns:1fr}
  .docs{position:static;flex-direction:row;overflow-x:auto}
  .doc{min-width:200px}
}
@media (max-width:760px){
  .app{grid-template-columns:1fr;grid-template-rows:auto auto 1fr}
  .top{flex-wrap:wrap;padding:8px 16px;gap:8px}
  .brand span{display:none}
  .search{order:5;flex-basis:100%;max-width:none}
  .search kbd{display:none}
  .chipbtn.live,.chipbtn.snap{display:none}
  .side{flex-direction:row;overflow-x:auto;border-right:0;border-bottom:1px solid var(--line);padding:6px 10px;gap:4px}
  .side .sep,.side .foot{display:none}
  .nav{white-space:nowrap;width:auto;padding:6px 10px}
  .nav .n{margin-left:2px}
  .wrap{padding:16px 16px 48px}
  .g-2,.g-3{grid-template-columns:1fr}
  .g-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}
  .day{grid-template-columns:1fr}
  .day .dl{position:static;padding-top:6px}
  .frow .fl{width:100%}
  .lb{grid-template-columns:1fr;grid-template-rows:1fr auto}
  .lb .info{border-left:0;border-top:1px solid #2d2d2a;max-height:42vh}
  .lb .x{right:10px}
  .kv{grid-template-columns:96px 1fr}
  .db{padding:14px 16px 40px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto!important}}
</style>
</head>
<body>
<div class="app">
  <header class="top">
    <button class="brand" data-go="overview" title="Overview">
      <span class="mark"><svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></span>
      <span class="t"><b>PHP2Shell</b><span>evidence vault · October 2026</span></span>
    </button>
    <div class="search">
      <svg class="i" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="text" placeholder="Search sources, claims, events, notes" autocomplete="off" spellcheck="false" aria-label="Search the vault">
      <kbd>/</kbd>
      <div class="sres" id="sres" role="listbox"></div>
    </div>
    <button class="chipbtn snap" id="mode" data-go="about" title="Where the data comes from"><span class="dot"></span><span id="modeT">snapshot</span></button>
    <button class="chipbtn ver" id="ver" data-go="about" title="Version history">__APP_VERSION__</button>
    <button class="iconbtn" id="theme" title="Light or dark" aria-label="Toggle theme"></button>
  </header>
  <nav class="side" id="side"></nav>
  <main id="main"><div class="boot">Opening the vault…</div></main>
</div>
<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" aria-hidden="true"><div class="dh"><div class="crumbs" id="dcr"></div><button class="iconbtn" data-close="drawer" aria-label="Close"></button></div><div class="db" id="db"></div></aside>
<div class="lb" id="lb" role="dialog" aria-label="Screenshot viewer"></div>
<div class="tr-m" id="trm"><div class="tr-box"><div class="dh"><div class="crumbs" id="trt"></div><button class="iconbtn" data-close="text" aria-label="Close"></button></div><div id="trb" style="display:flex;flex-direction:column;flex:1;min-height:0"></div></div></div>

<script>
const SNAPSHOT = /*__SNAPSHOT__*/null;
'use strict';
const APP_VERSION = '__APP_VERSION__';
const HAS_SG = typeof window.sg !== 'undefined' && window.sg && window.sg.vfs;
let READY_SENT = false;
function ready(){ if (READY_SENT) return; READY_SENT = true; try { window.parent && window.parent !== window && window.parent.postMessage({type:'sg-app-ready'}, '*'); } catch(e){} }

/* ---------- small helpers ---------- */
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const attr = esc;
const web = u => /^https?:\/\//i.test(String(u || '')) ? String(u) : '#';   // a source's URL from the vault: http(s) only
const plural = (n, w, p) => n + ' ' + (n === 1 ? w : (p || w + 's'));
const fmtBytes = n => n < 1024 ? n + ' B' : n < 1048576 ? (n/1024).toFixed(n < 10240 ? 1 : 0) + ' KB' : (n/1048576).toFixed(1) + ' MB';
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const pad = n => String(n).padStart(2, '0');
function norm(s){ return String(s || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, ''); }
function hl(text, q){
  const t = esc(text); if (!q) return t;
  const terms = q.split(/\s+/).filter(x => x.length > 1).map(x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!terms.length) return t;
  return t.replace(new RegExp('(' + terms.map(esc).join('|') + ')', 'gi'), '<mark>$1</mark>');
}
function matches(hay, q){ if (!q) return true; const h = norm(hay); return norm(q).split(/\s+/).filter(Boolean).every(w => h.includes(w)); }

const ICONS = {
  overview:'<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  sources:'<path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 3v5h5M8 13h8M8 17h6"/>',
  wall:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  claims:'<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
  timeline:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  desk:'<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  about:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  x:'<path d="M6 6l12 12M18 6 6 18"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/>',
  check:'<path d="m5 12 5 5 9-10"/>',
  quote:'<path d="M7 7h4v4c0 3-2 5-4 6M15 7h4v4c0 3-2 5-4 6"/>',
  alert:'<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17v.5"/>',
  ban:'<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
  xcirc:'<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
  star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
  ext:'<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  left:'<path d="m15 18-6-6 6-6"/>', right:'<path d="m9 18 6-6-6-6"/>',
  grid:'<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  rows:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  file:'<path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5"/>',
  hash:'<path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/>',
  camera:'<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  expand:'<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  text:'<path d="M5 6h14M5 10h14M5 14h10M5 18h8"/>'
};
const icon = (n, cls) => '<svg class="i' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" aria-hidden="true">' + (ICONS[n] || '') + '</svg>';

/* ---------- vocabularies ---------- */
const CLAIM_ST = {
  confirmed:   {cls:'p-good', ic:'check', label:'confirmed',   col:'var(--good)'},
  reported:    {cls:'p-info', ic:'quote', label:'reported',    col:'var(--info)'},
  disputed:    {cls:'p-ser',  ic:'alert', label:'disputed',    col:'var(--serious)'},
  contradicted:{cls:'p-crit', ic:'xcirc', label:'contradicted',col:'var(--critical)'},
  unverified:  {cls:'p-warn', ic:'help',  label:'unverified',  col:'var(--warning)'},
};
const CLAIM_ORDER = ['confirmed','reported','disputed','contradicted','unverified'];
const SRC_ST = {captured:{cls:'p-good',ic:'check'}, blocked:{cls:'p-warn',ic:'ban'}, failed:{cls:'p-crit',ic:'xcirc'}};
const PHASES = ['origin','discovery','coordination','leak','release','response','aftermath','method'];
const phaseColor = p => { const i = PHASES.indexOf(p); return i < 0 ? 'var(--neutral)' : 'var(--s' + (i + 1) + ')'; };
const claimPill = s => { const v = CLAIM_ST[s] || {cls:'p-mute', ic:'help', label:s || 'no status'}; return '<span class="pill ' + v.cls + '">' + icon(v.ic) + esc(v.label) + '</span>'; };
const srcPill = s => { const v = SRC_ST[s] || {cls:'p-mute', ic:'help'}; return '<span class="pill ' + v.cls + '">' + icon(v.ic) + esc(s || 'unknown') + '</span>'; };

/* ---------- dates ---------- */
function capDate(c){ const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(c || ''); return m ? new Date(Date.UTC(+m[1], m[2]-1, +m[3], +m[4], +m[5], +m[6])) : null; }
function fmtCap(c, withDate=true){ const d = capDate(c); if (!d) return c; return (withDate ? d.getUTCDate() + ' ' + MON[d.getUTCMonth()] + ' · ' : '') + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ':' + pad(d.getUTCSeconds()) + ' UTC'; }
/* A recorded date keeps its precision: a year stays a year. Returns {t: sortable ms, label, day, dayLabel, time} */
function parseAt(at){
  const s = String(at || '').trim();
  const first = s.split('/')[0];
  const m = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?Z?)?/.exec(first);
  if (!m) return {t: Infinity, label: s, day: 'undated', dayLabel: 'Undated', time: ''};
  const [, y, mo, d, h, mi, se] = m;
  const t = Date.UTC(+y, mo ? mo - 1 : 0, d ? +d : 1, h ? +h : 0, mi ? +mi : 0, se ? +se : 0);
  let dayKey, dayLabel, time = '';
  if (d){ dayKey = y + '-' + mo + '-' + d; const dt = new Date(t); dayLabel = d.replace(/^0/, '') + ' ' + MON[mo-1] + ' ' + y; dayLabel = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][dt.getUTCDay()] + ' ' + dayLabel; }
  else if (mo){ dayKey = y + '-' + mo; dayLabel = MON[mo-1] + ' ' + y; }
  else { dayKey = y; dayLabel = y; }
  if (h) time = h + ':' + mi + (se ? ':' + se : '') + ' UTC';
  let label = s.includes('/') ? s.split('/').map(x => { const p = parseAt(x); return p.dayLabel.replace(/^\w{3} /, ''); }).join(' – ') : (time ? dayLabel.replace(/^\w{3} /, '') + ' · ' + time : dayLabel.replace(/^\w{3} /, ''));
  if (s.includes('/')) { dayLabel = label; dayKey = s; }
  return {t, label, day: dayKey, dayLabel, time, precise: !!time};
}

/* ---------- markdown (escape first, then a small, safe subset) ---------- */
function inline(s){
  let t = esc(s);
  const codes = [];
  t = t.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, a, u) => '<a href="' + u + '" rel="noopener">' + a + '</a>');
  t = t.replace(/(^|[\s(])(https?:\/\/[^\s<)]+[^\s<).,;:'"])/g, (_, p, u) => p + '<a href="' + u + '" rel="noopener">' + u + '</a>');
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[^*\w])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>').replace(/(^|\s)_([^_\s][^_]*)_(?=\s|$|[.,;:])/g, '$1<em>$2</em>');
  return t.replace(/\u0000(\d+)\u0000/g, (_, i) => '<code>' + codes[+i] + '</code>');
}
function md(src){
  const L = String(src || '').replace(/\r\n?/g, '\n').split('\n'); const out = []; let i = 0;
  const isTable = j => /^\s*\|.*\|\s*$/.test(L[j] || '') && /^\s*\|?\s*:?-{2,}/.test(L[j + 1] || '');
  while (i < L.length){
    const l = L[i];
    if (/^```/.test(l)){ const buf = []; i++; while (i < L.length && !/^```/.test(L[i])) buf.push(L[i++]); i++; out.push('<pre><code>' + esc(buf.join('\n')) + '</code></pre>'); continue; }
    let m;
    if ((m = /^(#{1,6})\s+(.*)$/.exec(l))){ const n = Math.min(4, m[1].length); out.push('<h' + n + '>' + inline(m[2]) + '</h' + n + '>'); i++; continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(l)){ out.push('<hr>'); i++; continue; }
    if (isTable(i)){
      const row = r => r.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const head = row(L[i]); i += 2; const body = [];
      while (i < L.length && /^\s*\|/.test(L[i])) body.push(row(L[i++]));
      out.push('<table><thead><tr>' + head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>' + body.map(r => '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') + '</tbody></table>');
      continue;
    }
    if (/^\s*>/.test(l)){ const buf = []; while (i < L.length && /^\s*>/.test(L[i])) buf.push(L[i++].replace(/^\s*>\s?/, '')); out.push('<blockquote>' + md(buf.join('\n')) + '</blockquote>'); continue; }
    if (/^\s*([-*+]|\d+[.)])\s+/.test(l)){
      const ordered = /^\s*\d/.test(l); const items = [];
      while (i < L.length && (/^\s*([-*+]|\d+[.)])\s+/.test(L[i]) || (/^\s{2,}\S/.test(L[i]) && items.length))){
        if (/^\s*([-*+]|\d+[.)])\s+/.test(L[i])) items.push(L[i].replace(/^\s*([-*+]|\d+[.)])\s+/, '')); else items[items.length - 1] += ' ' + L[i].trim();
        i++;
      }
      out.push((ordered ? '<ol>' : '<ul>') + items.map(x => '<li>' + inline(x) + '</li>').join('') + (ordered ? '</ol>' : '</ul>'));
      continue;
    }
    if (!l.trim()){ i++; continue; }
    const buf = [l]; i++;
    while (i < L.length && L[i].trim() && !/^(#{1,6}\s|```|\s*>|\s*([-*+]|\d+[.)])\s)/.test(L[i]) && !isTable(i)) buf.push(L[i++]);
    out.push('<p>' + inline(buf.join(' ')) + '</p>');
  }
  return out.join('\n');
}
/* The memos are speech-to-text transcripts: "Name  0:00" lines then the words. */
function transcript(src){
  const parts = String(src || '').replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  for (const l of parts){
    if (!l.trim()) continue;
    const m = /^(.{2,40}?)\s{2,}(\d{1,2}:\d{2}(?::\d{2})?)\s*$/.exec(l);
    if (m) out.push('<span class="sp">' + esc(m[1]) + ' · ' + esc(m[2]) + '</span>'); else out.push('<p>' + inline(l) + '</p>');
  }
  return '<div class="md transcript">' + out.join('') + '</div>';
}

/* ---------- the data ---------- */
const D = {mode:'snapshot', sources:[], bySlug:{}, claims:[], events:[], captures:[], shots:{}, files:{}, notes:{}, memos:{}, deskNotes:{}, readme:'', versions:null, head:null, taken:null, built:null, citeC:{}, citeE:{}, missing:[]};

function agentOf(path){ return path.split('/').pop().replace(/\.json$/, ''); }
function ingest(src){
  D.sources = (src.sources || []).slice().sort((a, b) => a.slug.localeCompare(b.slug));
  D.bySlug = Object.fromEntries(D.sources.map(s => [s.slug, s]));
  D.claims = []; D.events = [];
  for (const [p, rows] of Object.entries(src.claims || {})) (Array.isArray(rows) ? rows : []).forEach((r, i) => D.claims.push(Object.assign({}, r, {_agent: agentOf(p), _file: p, _k: agentOf(p) + ':' + (r.id || i)})));
  for (const [p, rows] of Object.entries(src.timeline || {})) (Array.isArray(rows) ? rows : []).forEach((r, i) => { const pa = parseAt(r.at); D.events.push(Object.assign({}, r, {_agent: agentOf(p), _file: p, _p: pa, _k: agentOf(p) + ':' + i})); });
  D.events.sort((a, b) => a._p.t - b._p.t || a._agent.localeCompare(b._agent));
  const man = src.manifest || {};
  D.shots = man.shots || {}; D.files = man.files || {};
  if (src.source_notes) D.notes = Object.assign({}, src.source_notes, D.notes);
  if (src.memos) D.memos = src.memos;
  if (src.notes) D.deskNotes = src.notes;
  if (src.readme != null) D.readme = src.readme;
  if (src.versions) D.versions = src.versions;
  D.head = src.vault_head || D.head; D.built = man.built_utc || D.built;
  // derived
  D.captures = [];
  for (const s of D.sources) for (const c of (s.captures || [])) D.captures.push({slug: s.slug, cap: c, d: capDate(c), shot: (D.shots[s.slug] || {})[c] || null});
  D.captures.sort((a, b) => (b.d || 0) - (a.d || 0));
  D.citeC = {}; D.citeE = {}; const miss = {};
  for (const c of D.claims) for (const sl of (c.sources || [])) { (D.citeC[sl] = D.citeC[sl] || []).push(c); if (!D.bySlug[sl]) (miss[sl] = miss[sl] || []).push('claim ' + c._k); }
  for (const e of D.events) for (const sl of (e.sources || [])) { (D.citeE[sl] = D.citeE[sl] || []).push(e); if (!D.bySlug[sl]) (miss[sl] = miss[sl] || []).push('event ' + e._k); }
  D.missing = Object.entries(miss).map(([slug, by]) => ({slug, by}));
}
const cites = slug => (D.citeC[slug] || []).length + (D.citeE[slug] || []).length;
const latestShot = s => { const caps = (s.captures || []).slice().sort().reverse(); for (const c of caps) { const sh = (D.shots[s.slug] || {})[c]; if (sh) return {cap: c, shot: sh}; } return null; };
const pubShort = s => (s && s.publisher || '').replace(/\s*\(.*?\)\s*/g, ' ').trim();

async function readJSON(p){ return JSON.parse(await sg.vfs.readText(p)); }
async function listJSON(prefix){
  const rows = await sg.vfs.list(prefix);
  return (rows || []).map(r => r.path || r.name).filter(Boolean).map(p => p.startsWith(prefix + '/') ? p : (prefix + '/' + p.replace(/^\/+/, ''))).filter(p => /\.json$/.test(p) && p.split('/').length === 2);
}
async function loadLive(){
  if (!HAS_SG) return false;
  const live = {};
  live.sources = await readJSON('sources/index.json');
  const snapC = Object.keys((SNAPSHOT || {}).claims || {}), snapT = Object.keys((SNAPSHOT || {}).timeline || {});
  let cl = snapC, tl = snapT;
  try { cl = await listJSON('claims'); } catch(e){}
  try { tl = await listJSON('timeline'); } catch(e){}
  live.claims = {}; live.timeline = {};
  await Promise.all(cl.map(async p => { try { live.claims[p] = await readJSON(p); } catch(e){} }));
  await Promise.all(tl.map(async p => { try { live.timeline[p] = await readJSON(p); } catch(e){} }));
  try { live.manifest = await readJSON('app/manifest.json'); } catch(e){ live.manifest = (SNAPSHOT || {}).manifest; }
  try { live.readme = await sg.vfs.readText('README.md'); } catch(e){}
  try { live.versions = await readJSON('app/versions/index.json'); } catch(e){}
  live.vault_head = (SNAPSHOT || {}).vault_head;
  D.notes = {}; // re-read on demand from the vault
  ingest(Object.assign({}, live, {memos: D.memos, notes: D.deskNotes}));
  // memos and notes: list live so new ones show
  try {
    const listAll = async pre => (await sg.vfs.list(pre) || []).map(r => r.path || r.name).filter(Boolean).map(p => p.startsWith(pre + '/') ? p : pre + '/' + p).filter(p => p.split('/').length === 2);
    const mm = await listAll('memos'), nn = await listAll('notes');
    const memos = {}, notes = {};
    await Promise.all(mm.map(async p => { try { memos[p] = await sg.vfs.readText(p); } catch(e){} }));
    await Promise.all(nn.map(async p => { try { notes[p] = await sg.vfs.readText(p); } catch(e){} }));
    if (Object.keys(memos).length) D.memos = memos;
    if (Object.keys(notes).length) D.deskNotes = notes;
  } catch(e){}
  D.mode = 'live';
  return true;
}
async function sourceNotes(slug){
  if (D.notes[slug] != null) return D.notes[slug];
  if (HAS_SG){ try { return (D.notes[slug] = await sg.vfs.readText('sources/' + slug + '/notes.md')); } catch(e){} }
  const snap = ((SNAPSHOT || {}).source_notes || {})[slug];
  return (D.notes[slug] = snap != null ? snap : '');
}

/* ---------- UI state ---------- */
const S = {
  view:'overview', theme:null,
  src:{q:'', kind:null, status:null, primary:null, agent:null, sort:'cited', layout:'cards'},
  wall:{q:'', kind:null, bin:null, order:'desc'},
  cl:{q:'', status:null, topic:null, agent:null, group:'topic'},
  tl:{q:'', phase:null, conf:null, agent:null},
  desk:null,
};
const store = {
  async get(k){ try { if (HAS_SG && sg.state) return await Promise.race([sg.state.get(k), new Promise(r => setTimeout(() => r(null), 600))]); } catch(e){} return null; },
  set(k, v){ try { if (HAS_SG && sg.state) sg.state.set(k, v); } catch(e){} }
};
function persist(){ store.set('ui', {view: S.view, theme: S.theme, layout: S.src.layout, group: S.cl.group, order: S.wall.order}); }

/* ---------- shell ---------- */
const VIEWS = [
  ['overview','Overview'], ['sources','Sources'], ['wall','Evidence wall'], ['claims','Claims'], ['timeline','Timeline'], ['desk','Desk'], ['about','About']
];
function counts(){ return {sources: D.sources.length, wall: D.captures.length, claims: D.claims.length, timeline: D.events.length, desk: Object.keys(D.memos).length + Object.keys(D.deskNotes).length + 1}; }
function renderSide(){
  const n = counts();
  $('#side').innerHTML = VIEWS.map(([k, l], i) => (i === 6 ? '<div class="sep"></div>' : '') +
    '<button class="nav' + (S.view === k ? ' on' : '') + '" data-go="' + k + '">' + icon(k) + '<span>' + l + '</span>' + (n[k] != null ? '<span class="n">' + n[k] + '</span>' : '') + '</button>').join('') +
    '<div class="foot"><b>' + (D.mode === 'live' ? 'Live' : 'Snapshot') + '</b> · ' + (D.mode === 'live' ? 'read from this vault just now' : 'built ' + esc(D.taken || D.built || '')) +
    (D.head ? '<br>vault head at build <span class="mono">' + esc(D.head) + '</span>' : '') + '<br>Private evidence: quote and link, never republish.</div>';
  const mode = $('#mode'); mode.className = 'chipbtn ' + (D.mode === 'live' ? 'live' : 'snap');
  $('#modeT').textContent = D.mode === 'live' ? 'live from vault' : 'snapshot ' + (D.taken || '').replace('T', ' ');
}
function setTheme(t){
  S.theme = t;
  if (t) document.documentElement.setAttribute('data-theme', t); else document.documentElement.removeAttribute('data-theme');
  const dark = t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  $('#theme').innerHTML = icon(dark ? 'sun' : 'moon');
}
function go(view, preset){
  if (preset) for (const [k, v] of Object.entries(preset)) Object.assign(S[k], v);
  S.view = view; persist(); renderSide(); render();
  $('#main').scrollTop = 0;
}
function render(){
  const m = $('#main');
  const fn = {overview: vOverview, sources: vSources, wall: vWall, claims: vClaims, timeline: vTimeline, desk: vDesk, about: vAbout}[S.view] || vOverview;
  m.innerHTML = '<div class="wrap">' + fn() + footer() + '</div>';
  after();
}
function footer(){
  return '<div class="foot2">' + icon('lock') + '<span>An app on top of an encrypted SG/Vault, rendered straight from it. The app, the claims, the timeline and the notes are ours (CC BY 4.0). Captured pages, screenshots and quoted words belong to their publishers and authors, are credited on each source, and are held as evidence, not for republication.</span><span style="margin-left:auto" class="mono">' + esc(APP_VERSION) + (D.head ? ' · vault ' + esc(D.head) : '') + '</span></div>';
}
/* images are always assigned from JS (the bridge routes img.src) */
function after(){
  for (const img of $$('img[data-src]')){
    const p = img.getAttribute('data-src'); img.removeAttribute('data-src');
    img.onload = () => img.classList.add('ok');
    img.onerror = () => { const ph = img.parentNode.querySelector('.ph'); if (ph) ph.style.display = ''; img.remove(); };
    img.src = p;
  }
  for (const f of $$('[data-fill]')){ const k = f.getAttribute('data-fill'); f.removeAttribute('data-fill'); FILL[k] && FILL[k](f); }
}
const FILL = {};
function thumbHTML(shot, s, extra){
  const ph = '<div class="ph"' + (shot ? ' style="display:none"' : '') + '>' + (s && s.status !== 'captured' ? icon(s.status === 'blocked' ? 'ban' : 'xcirc') + (s.status === 'blocked' ? 'Blocked at capture' : 'Capture failed') : icon('camera') + 'No screenshot') + '</div>';
  return '<div class="thumb">' + (shot ? '<img alt="" loading="lazy" data-src="' + attr(shot.thumb) + '">' : '') + ph + (extra || '') + '</div>';
}

/* ---------- overview ---------- */
function vOverview(){
  const n = D.sources.length, cap = D.sources.filter(s => s.status === 'captured').length;
  const stc = {}; D.sources.forEach(s => stc[s.status] = (stc[s.status] || 0) + 1);
  const cst = {}; D.claims.forEach(c => cst[c.status] = (cst[c.status] || 0) + 1);
  const shots = D.captures.filter(c => c.shot).length;
  const prim = D.sources.filter(s => s.primary).length;
  const agents = new Set([...D.sources.map(s => s.added_by), ...D.claims.map(c => c._agent), ...D.events.map(e => e._agent)].filter(Boolean));
  const opened = (D.readme.match(/opened at ([0-9T:\-]+Z)/) || [])[1];
  const lead = (D.readme.split('\n\n')[1] || '').replace(/\n/g, ' ');
  const tiles = [
    ['sources', 'Sources', n, (stc.captured || 0) + ' captured · ' + (stc.blocked || 0) + ' blocked' + (stc.failed ? ' · ' + stc.failed + ' failed' : '')],
    ['wall', 'Captures', D.captures.length, shots + ' with a screenshot'],
    ['claims', 'Claims', D.claims.length, (cst.confirmed || 0) + ' confirmed · ' + ((cst.disputed || 0) + (cst.contradicted || 0)) + ' disputed'],
    ['timeline', 'Timeline events', D.events.length, D.events.filter(e => e.confidence === 'inferred').length + ' inferred'],
    ['sources:primary', 'Primary sources', prim, Math.round(100 * prim / Math.max(1, n)) + '% of sources'],
    ['about', 'Agents writing', agents.size, 'and the editor'],
  ];
  const retry = D.sources.filter(s => s.status !== 'captured');
  const contested = D.claims.filter(c => ['disputed','contradicted','unverified'].includes(c.status));
  const confirmed = D.claims.filter(c => c.status === 'confirmed');
  return '<div class="vh"><div class="grow"><p class="kicker">Evidence vault' + (opened ? ' · opened ' + esc(fmtIso(opened)) : '') + '</p>' +
    '<h1>The two PHP flaws of October 2026: everything captured, every claim, every source</h1>' +
    '<p class="lead">' + inline(lead || 'The evidence behind the story.') + '</p></div></div>' +
    '<div class="grid g-tiles">' + tiles.map(([g, l, v, s]) => '<button class="tile" data-go="' + g + '"><div class="l">' + l + '</div><div class="v">' + v + '</div><div class="s">' + esc(s) + '</div></button>').join('') + '</div>' +
    '<div class="grid g-2 sect">' +
      '<div class="panel"><div class="sect-h"><h2>Claims by status</h2><button class="more" data-go="claims">All claims</button></div>' + claimStack(cst) +
        '<p class="small muted" style="margin:.8rem 0 0">A status says what the evidence supports, not whether a claim is true. Each agent keeps its own claims file; the app merges them.</p></div>' +
      '<div class="panel"><div class="sect-h"><h2>When the captures were taken</h2><button class="more" data-go="wall">Evidence wall</button></div><div class="chart" data-fill="hours"></div></div>' +
    '</div>' +
    '<div class="grid g-3 sect">' +
      '<div class="panel"><div class="sect-h"><h2>Sources by kind</h2></div>' + kindBars() + '</div>' +
      '<div class="panel"><div class="sect-h"><h2>Needs another look</h2></div>' + attention(retry, contested) + '</div>' +
      '<div class="panel"><div class="sect-h"><h2>Confirmed</h2><button class="more" data-go="claims" data-preset=\'{"cl":{"status":"confirmed"}}\'>' + confirmed.length + '</button></div><ul class="att">' +
        confirmed.slice(0, 6).map(c => '<li><button class="clear" style="color:var(--fg);text-align:left" data-claim="' + attr(c._k) + '">' + icon('check') + ' ' + esc(c.claim) + '</button><span class="x">' + esc(c.by || '') + ' · ' + plural((c.sources || []).length, 'source') + '</span></li>').join('') + '</ul></div>' +
    '</div>' +
    '<div class="sect"><div class="sect-h"><h2>Latest captures</h2><button class="more" data-go="wall">All ' + D.captures.length + '</button></div><div class="strip">' +
      D.captures.filter(c => c.shot).slice(0, 12).map(shotHTML).join('') + '</div></div>' +
    '<div class="sect"><div class="sect-h"><h2>Who wrote what</h2></div>' + agentTable() + '</div>' +
    integrity();
}
function fmtIso(s){ const p = parseAt(s); return p.label; }
function claimStack(cst){
  const tot = D.claims.length || 1;
  const keys = CLAIM_ORDER.filter(k => cst[k]).concat(Object.keys(cst).filter(k => !CLAIM_ORDER.includes(k)));
  return '<div class="stack" role="img" aria-label="Claims by status">' + keys.map(k => '<button title="' + attr((cst[k]) + ' ' + k) + '" style="flex:' + cst[k] + ';background:' + (CLAIM_ST[k] || {col:'var(--neutral)'}).col + '" data-go="claims" data-preset=\'{"cl":{"status":"' + attr(k) + '"}}\'></button>').join('') + '</div>' +
    '<div class="legend">' + keys.map(k => '<button data-go="claims" data-preset=\'{"cl":{"status":"' + attr(k) + '"}}\'>' + claimPill(k) + '<b>' + cst[k] + '</b><span class="muted small">' + Math.round(100 * cst[k] / tot) + '%</span></button>').join('') + '</div>';
}
function kindBars(){
  const kc = {}; D.sources.forEach(s => kc[s.kind] = (kc[s.kind] || 0) + 1);
  const rows = Object.entries(kc).sort((a, b) => b[1] - a[1]); const max = rows[0] ? rows[0][1] : 1;
  return rows.map(([k, v]) => '<button class="hbar" data-go="sources" data-preset=\'{"src":{"kind":"' + attr(k) + '"}}\' title="' + attr(v + ' ' + k) + '"><span class="nm">' + esc(k) + '</span><span class="tr"><i style="width:' + (100 * v / max) + '%"></i></span><span>' + v + '</span></button>').join('');
}
function attention(retry, contested){
  return '<ul class="att">' + retry.slice(0, 5).map(s => '<li>' + srcPill(s.status) + ' <button class="clear" style="color:var(--fg)" data-src="' + attr(s.slug) + '">' + esc(pubShort(s) || s.slug) + '</button><span class="x">' + esc(s.title || s.url) + '</span></li>').join('') +
    (retry.length > 5 ? '<li><button class="clear" data-go="sources" data-preset=\'{"src":{"status":"blocked"}}\'>All ' + retry.length + ' not captured</button></li>' : '') +
    contested.slice(0, 4).map(c => '<li>' + claimPill(c.status) + ' <button class="clear" style="color:var(--fg);text-align:left" data-claim="' + attr(c._k) + '">' + esc(c.claim) + '</button></li>').join('') +
    (contested.length > 4 ? '<li><button class="clear" data-go="claims" data-preset=\'{"cl":{"status":"disputed"}}\'>All ' + contested.length + ' contested or unverified</button></li>' : '') + '</ul>';
}
function agentTable(){
  const A = {};
  const row = a => A[a] = A[a] || {s:0, c:0, e:0, cap:0};
  D.sources.forEach(s => { row(s.added_by || 'unknown').s++; row(s.added_by || 'unknown').cap += (s.captures || []).length; });
  D.claims.forEach(c => row(c._agent).c++); D.events.forEach(e => row(e._agent).e++);
  const rows = Object.entries(A).sort((a, b) => (b[1].s + b[1].c + b[1].e) - (a[1].s + a[1].c + a[1].e));
  return '<div class="tscroll"><table class="tbl agents"><thead><tr><th>Agent</th><th class="num">Sources added</th><th class="num">Their captures</th><th class="num">Claims</th><th class="num">Timeline events</th></tr></thead><tbody>' +
    rows.map(([a, r]) => '<tr data-go="sources" data-preset=\'{"src":{"agent":"' + attr(a) + '"}}\'><td>' + icon('user') + ' <span class="mono">' + esc(a) + '</span></td><td class="num">' + r.s + '</td><td class="num">' + r.cap + '</td><td class="num">' + r.c + '</td><td class="num">' + r.e + '</td></tr>').join('') + '</tbody></table></div>';
}
function integrity(){
  const noShot = D.captures.filter(c => !c.shot).length;
  const parts = [];
  parts.push(D.missing.length ? '<li>' + claimPill('disputed') + ' ' + plural(D.missing.length, 'cited slug') + ' not in <span class="mono">sources/index.json</span>: ' + D.missing.map(m => '<span class="mono">' + esc(m.slug) + '</span>').join(', ') + '</li>' : '<li>' + icon('check') + ' Every slug cited by a claim or an event is in the manifest.</li>');
  parts.push('<li>' + icon('camera') + ' ' + plural(noShot, 'capture') + ' without a reduced screenshot in <span class="mono">app/shots/</span>' + (noShot ? ' (newer than the last app build, or the capture has none)' : '') + '.</li>');
  return '<div class="sect panel"><div class="sect-h"><h2>Integrity checks</h2><span class="small muted">computed in your browser from the files</span></div><ul class="att">' + parts.join('') + '</ul></div>';
}
function binSize(){
  const ts = D.captures.filter(c => c.d).map(c => +c.d); if (!ts.length) return 60;
  const span = (Math.max(...ts) - Math.min(...ts)) / 3600e3;
  return span <= 12 ? 15 : span <= 72 ? 60 : 1440;
}
const binKey = (d, m) => new Date(Math.floor(+d / (m * 60e3)) * m * 60e3).toISOString().slice(0, 16);
function binLabel(k, m){
  const d = new Date(k + ':00Z'), e = new Date(+d + m * 60e3 - 1);
  const hm = x => pad(x.getUTCHours()) + ':' + pad(x.getUTCMinutes());
  return d.getUTCDate() + ' ' + MON[d.getUTCMonth()] + (m >= 1440 ? '' : ' · ' + hm(d) + '–' + hm(e) + ' UTC');
}
FILL.hours = el => {
  const m = binSize(), bins = {};
  D.captures.forEach(c => { if (!c.d) return; const k = binKey(c.d, m); bins[k] = (bins[k] || 0) + 1; });
  const keys = Object.keys(bins).sort();
  if (!keys.length){ el.innerHTML = '<p class="muted small">No captures yet.</p>'; return; }
  const first = +new Date(keys[0] + ':00Z'), last = +new Date(keys[keys.length - 1] + ':00Z');
  const hrs = []; for (let t = first; t <= last; t += m * 60e3) hrs.push(new Date(t).toISOString().slice(0, 16));
  const W = 560, H = 190, pl = 30, pb = 26, pt = 10, bw = (W - pl) / hrs.length;
  const max = Math.max(...hrs.map(h => bins[h] || 0)); const step = max > 80 ? 40 : max > 40 ? 20 : max > 16 ? 10 : 5; const top = Math.ceil(max / step) * step;
  const y = v => pt + (H - pt - pb) * (1 - v / top);
  let g = '';
  for (let v = 0; v <= top; v += step) g += '<line class="gl" x1="' + pl + '" x2="' + W + '" y1="' + y(v) + '" y2="' + y(v) + '"/><text class="tick" x="' + (pl - 6) + '" y="' + (y(v) + 3) + '" text-anchor="end">' + v + '</text>';
  const every = Math.max(1, Math.ceil(hrs.length / 8));
  hrs.forEach((h, i) => {
    const v = bins[h] || 0, x = pl + i * bw + 1, w = Math.max(2, bw - 2), yy = y(v), hgt = H - pb - yy, r = Math.min(4, hgt, w / 2);
    if (v) g += '<g class="b" data-go="wall" data-preset=\'{"wall":{"bin":"' + h + '|' + m + '"}}\' data-tip="' + attr(binLabel(h, m) + ' · ' + plural(v, 'capture')) + '"><rect class="hit" x="' + (pl + i * bw) + '" y="' + pt + '" width="' + bw + '" height="' + (H - pt - pb) + '"/>' +
      '<path class="bar" d="M' + x + ',' + (H - pb) + 'V' + (yy + r) + 'q0,-' + r + ' ' + r + ',-' + r + 'H' + (x + w - r) + 'q' + r + ',0 ' + r + ',' + r + 'V' + (H - pb) + 'z"/></g>';
    if (i % every === 0) g += '<text class="tick" x="' + (pl + i * bw + bw / 2) + '" y="' + (H - pb + 14) + '" text-anchor="middle">' + (m >= 1440 ? h.slice(8, 10) + ' ' + MON[+h.slice(5, 7) - 1] : h.slice(11, 16)) + '</text>';
  });
  g += '<line class="ax" x1="' + pl + '" x2="' + W + '" y1="' + (H - pb) + '" y2="' + (H - pb) + '"/>';
  const unit = m >= 1440 ? 'day' : m === 60 ? 'hour' : m + ' minutes';
  el.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Captures per ' + unit + '">' + g + '</svg><div class="tip"></div><p class="tiny muted" style="margin:6px 0 0">Captures per ' + unit + ', UTC, ' + binLabel(keys[0], 1440) + (keys[0].slice(0, 10) !== keys[keys.length - 1].slice(0, 10) ? ' to ' + binLabel(keys[keys.length - 1], 1440) : '') + '. Click a bar to see those screenshots.</p>';
  const tip = el.querySelector('.tip');
  el.addEventListener('mousemove', e => { const b = e.target.closest('g.b'); if (!b){ tip.style.opacity = 0; return; } const rc = el.getBoundingClientRect(); tip.textContent = b.getAttribute('data-tip'); tip.style.left = (e.clientX - rc.left) + 'px'; tip.style.top = (e.clientY - rc.top) + 'px'; tip.style.opacity = 1; });
  el.addEventListener('mouseleave', () => tip.style.opacity = 0);
};

/* ---------- sources ---------- */
function facet(group, key, label, values, counts, fmt){
  const cur = S[group][key];
  return '<div class="frow"><span class="fl">' + label + '</span>' + values.map(v => '<button class="chip' + (cur === v ? ' on' : '') + '" data-f="' + group + ':' + key + ':' + attr(v) + '">' + (fmt ? fmt(v) : esc(v)) + '<span class="c">' + (counts[v] || 0) + '</span></button>').join('') + '</div>';
}
const countBy = (rows, f) => { const o = {}; rows.forEach(r => { const k = f(r); if (k != null) o[k] = (o[k] || 0) + 1; }); return o; };
function filteredSources(){
  const f = S.src;
  let rows = D.sources.filter(s => (!f.kind || s.kind === f.kind) && (!f.status || s.status === f.status) && (f.primary == null || String(!!s.primary) === f.primary) && (!f.agent || s.added_by === f.agent) &&
    matches([s.slug, s.title, s.publisher, s.url, s.notes, s.kind, D.notes[s.slug] || ''].join(' '), f.q));
  const sorts = {
    cited: (a, b) => cites(b.slug) - cites(a.slug) || a.slug.localeCompare(b.slug),
    captured: (a, b) => ((b.captures || []).slice(-1)[0] || '').localeCompare((a.captures || []).slice(-1)[0] || ''),
    published: (a, b) => String(b.published || '').localeCompare(String(a.published || '')),
    publisher: (a, b) => (a.publisher || '').localeCompare(b.publisher || ''),
  };
  return rows.sort(sorts[f.sort] || sorts.cited);
}
function vSources(){
  const f = S.src;
  const any = f.kind || f.status || f.primary != null || f.agent || f.q;
  return '<div class="vh"><div class="grow"><p class="kicker">Sources</p><h1>Every source in the vault</h1><p class="lead">One folder per URL: the row in <span class="mono">source.json</span>, the agent\'s notes, and every capture with its hashes. Captures are additive; a live page gets a new capture each time someone looks.</p></div></div>' +
    '<div class="toolbar"><div class="fsearch">' + icon('search') + '<input id="fq" data-q="src" value="' + attr(f.q) + '" placeholder="Filter by publisher, title, URL, notes"></div>' +
    '<select class="sel" data-sort="src"><option value="cited"' + (f.sort === 'cited' ? ' selected' : '') + '>Most cited</option><option value="captured"' + (f.sort === 'captured' ? ' selected' : '') + '>Latest capture</option><option value="published"' + (f.sort === 'published' ? ' selected' : '') + '>Published</option><option value="publisher"' + (f.sort === 'publisher' ? ' selected' : '') + '>Publisher A–Z</option></select>' +
    '<div class="seg"><button data-layout="cards" class="' + (f.layout === 'cards' ? 'on' : '') + '">' + icon('grid') + 'Cards</button><button data-layout="table" class="' + (f.layout === 'table' ? 'on' : '') + '">' + icon('rows') + 'Table</button></div>' +
    (any ? '<button class="clear" data-reset="src">Clear filters</button>' : '') + '<span class="count" id="cnt"></span></div>' +
    '<div class="facets">' +
      facet('src', 'kind', 'Kind', Object.keys(countBy(D.sources, s => s.kind)).sort(), countBy(D.sources, s => s.kind)) +
      facet('src', 'status', 'Status', ['captured','blocked','failed'].filter(x => D.sources.some(s => s.status === x)), countBy(D.sources, s => s.status)) +
      facet('src', 'primary', 'Primary', ['true','false'], countBy(D.sources, s => String(!!s.primary)), v => v === 'true' ? 'primary' : 'secondary') +
      facet('src', 'agent', 'Added by', Object.keys(countBy(D.sources, s => s.added_by)).sort(), countBy(D.sources, s => s.added_by)) +
    '</div><div id="list"></div>';
}
function renderSourceList(){
  const rows = filteredSources(); const el = $('#list'); if (!el) return;
  $('#cnt').textContent = rows.length + ' of ' + D.sources.length;
  if (!rows.length){ el.innerHTML = '<div class="empty">No source matches. <button class="clear" data-reset="src">Clear filters</button></div>'; return; }
  const q = S.src.q;
  if (S.src.layout === 'table'){
    el.innerHTML = '<div class="tscroll"><table class="tbl"><thead><tr><th>Publisher</th><th>Title</th><th>Kind</th><th>Status</th><th>Published</th><th class="num">Captures</th><th class="num">Cited</th><th>Added by</th></tr></thead><tbody>' +
      rows.map(s => '<tr data-src="' + attr(s.slug) + '"><td>' + (s.primary ? icon('star') + ' ' : '') + hl(pubShort(s), q) + '</td><td>' + hl(s.title || s.url, q) + '<div class="tiny muted mono">' + esc(s.slug) + '</div></td><td><span class="pill p-kind">' + esc(s.kind) + '</span></td><td>' + srcPill(s.status) + '</td><td class="small">' + esc(s.published || '') + '</td><td class="num">' + (s.captures || []).length + '</td><td class="num">' + cites(s.slug) + '</td><td class="small mono">' + esc(s.added_by || '') + '</td></tr>').join('') + '</tbody></table></div>';
  } else {
    el.innerHTML = '<div class="grid g-cards">' + rows.map(s => cardHTML(s, q)).join('') + '</div>';
  }
  after();
}
function cardHTML(s, q){
  const ls = latestShot(s); const n = (s.captures || []).length;
  return '<button class="card" data-src="' + attr(s.slug) + '">' + thumbHTML(ls && ls.shot, s, '<div class="ov">' + (s.primary ? '<span class="pill p-prim">' + icon('star') + 'primary</span>' : '') + (s.status !== 'captured' ? srcPill(s.status) : '') + '</div>' + (n > 1 ? '<span class="ncap">' + n + ' captures</span>' : '')) +
    '<div class="b"><div class="pub"><span class="pill p-kind">' + esc(s.kind) + '</span><span>' + hl(pubShort(s), q) + '</span></div><div class="ti">' + hl(s.title || s.url, q) + '</div>' +
    '<div class="ft"><span>' + esc(s.published ? 'published ' + String(s.published).slice(0, 16) : 'no date stated') + '</span><span>' + plural(cites(s.slug), 'citation') + '</span></div></div></button>';
}

/* ---------- evidence wall ---------- */
function shotHTML(c){
  const s = D.bySlug[c.slug] || {};
  return '<button class="shot" data-cap="' + attr(c.slug + '|' + c.cap) + '" title="' + attr((s.publisher || '') + ': ' + (s.title || '')) + '">' + thumbHTML(c.shot, s) + '<div class="cap"><b>' + esc(pubShort(s) || c.slug) + '</b>' + esc(fmtCap(c.cap)) + '</div></button>';
}
function wallRows(){
  const f = S.wall;
  let rows = D.captures.filter(c => c.shot && (!f.kind || (D.bySlug[c.slug] || {}).kind === f.kind) && (!f.bin || (c.d && binKey(c.d, +f.bin.split('|')[1]) === f.bin.split('|')[0])) && (!f.q || matches([c.slug, (D.bySlug[c.slug] || {}).title, (D.bySlug[c.slug] || {}).publisher].join(' '), f.q)));
  if (f.order === 'asc') rows = rows.slice().reverse();
  return rows;
}
function vWall(){
  const f = S.wall;
  const all = D.captures.filter(c => c.shot);
  return '<div class="vh"><div class="grow"><p class="kicker">Evidence wall</p><h1>Every screenshot, in the order it was taken</h1><p class="lead">What each page looked like when an agent captured it. Open one to read the page at full width, step through the others, or open the full-resolution original whose hash is in the capture\'s provenance.</p></div></div>' +
    '<div class="toolbar"><div class="fsearch">' + icon('search') + '<input data-q="wall" value="' + attr(f.q) + '" placeholder="Filter by publisher or title"></div>' +
    '<div class="seg"><button data-order="desc" class="' + (f.order === 'desc' ? 'on' : '') + '">Newest first</button><button data-order="asc" class="' + (f.order === 'asc' ? 'on' : '') + '">Oldest first</button></div>' +
    (f.bin ? '<button class="chip on" data-f="wall:bin:' + attr(f.bin) + '">' + esc(binLabel(f.bin.split('|')[0], +f.bin.split('|')[1])) + ' ' + icon('x') + '</button>' : '') +
    ((f.kind || f.q || f.bin) ? '<button class="clear" data-reset="wall">Clear filters</button>' : '') + '<span class="count" id="cnt"></span></div>' +
    '<div class="facets">' + facet('wall', 'kind', 'Kind', Object.keys(countBy(all, c => (D.bySlug[c.slug] || {}).kind)).sort(), countBy(all, c => (D.bySlug[c.slug] || {}).kind)) + '</div><div id="list"></div>';
}
function renderWallList(){
  const rows = wallRows(); const el = $('#list'); if (!el) return;
  $('#cnt').textContent = rows.length + ' of ' + D.captures.filter(c => c.shot).length + ' screenshots';
  if (!rows.length){ el.innerHTML = '<div class="empty">No screenshot matches.</div>'; return; }
  let html = '', cur = null, buf = [];
  const flush = () => { if (buf.length) html += '<div class="hour-h">' + esc(cur) + ' <span>· ' + buf.length + '</span></div><div class="grid g-wall">' + buf.join('') + '</div>'; buf = []; };
  for (const c of rows){ const h = c.d ? c.d.getUTCDate() + ' ' + MON[c.d.getUTCMonth()] + ' ' + pad(c.d.getUTCHours()) + ':00 UTC' : 'undated'; if (h !== cur){ flush(); cur = h; } buf.push(shotHTML(c)); }
  flush(); el.innerHTML = html; after();
}

/* ---------- claims ---------- */
function filteredClaims(){
  const f = S.cl;
  return D.claims.filter(c => (!f.status || c.status === f.status || (f.status === 'disputed' && c.status === 'contradicted')) && (!f.topic || (c.topic || 'untagged') === f.topic) && (!f.agent || c._agent === f.agent) &&
    matches([c.claim, c.by, c.note, c.id, (c.sources || []).join(' ')].join(' '), f.q));
}
function srcChips(slugs){
  const seen = {}; (slugs || []).forEach(sl => { const k = pubShort(D.bySlug[sl]); seen[k] = (seen[k] || 0) + 1; });
  const name = (s, sl) => { const p = pubShort(s) || sl; if (seen[p] < 2) return p; const t = (s.title || sl).replace(/^\W+/, ''); return p + ': ' + (t.length > 34 ? t.slice(0, 32) + '…' : t); };
  return '<div class="srcs">' + (slugs || []).map(sl => { const s = D.bySlug[sl]; return s ? '<button class="sc" data-src="' + attr(sl) + '" title="' + attr((s.publisher || '') + ': ' + (s.title || sl)) + '">' + (s.primary ? icon('star') : icon('file')) + '<span>' + esc(name(s, sl)) + '</span>' + (s.status !== 'captured' ? '<span class="st">· ' + esc(s.status) + '</span>' : '') + '</button>' : '<span class="sc miss" title="Not in sources/index.json">' + icon('alert') + '<span>' + esc(sl) + '</span></span>'; }).join('') + '</div>';
}
function claimHTML(c, q){
  const n = (c.sources || []).length, p = (c.sources || []).filter(sl => (D.bySlug[sl] || {}).primary).length;
  return '<article class="claim" id="c-' + attr(c._k) + '"><div class="top1">' + claimPill(c.status) + (c.topic ? '<span class="pill p-line">' + esc(c.topic) + '</span>' : '') + '<span class="tiny muted mono" style="margin-left:auto">' + esc(c.id || '') + '</span></div>' +
    '<div class="txt">' + hl(c.claim, q) + '</div>' + (c.by ? '<div class="by">Said by ' + hl(c.by, q) + '</div>' : '') + (c.note ? '<div class="note">' + hl(c.note, q) + '</div>' : '') +
    srcChips(c.sources) + '<div class="meta">' + icon('user') + '<span class="mono">' + esc(c._agent) + '</span><span>·</span><span>' + plural(n, 'source') + (p ? ', ' + p + ' primary' : '') + '</span></div></article>';
}
function vClaims(){
  const f = S.cl; const any = f.status || f.topic || f.agent || f.q;
  return '<div class="vh"><div class="grow"><p class="kicker">Claims</p><h1>What was said, by whom, and what the evidence supports</h1><p class="lead">Confirmed: a primary source shows it. Reported: someone credible says it and it is cited. Disputed: sources disagree. Unverified: nobody has shown it, including the people repeating it.</p></div></div>' +
    '<div class="toolbar"><div class="fsearch">' + icon('search') + '<input data-q="cl" value="' + attr(f.q) + '" placeholder="Filter claims, who said them, notes"></div>' +
    '<div class="seg"><button data-group="topic" class="' + (f.group === 'topic' ? 'on' : '') + '">By topic</button><button data-group="status" class="' + (f.group === 'status' ? 'on' : '') + '">By status</button><button data-group="agent" class="' + (f.group === 'agent' ? 'on' : '') + '">By agent</button></div>' +
    (any ? '<button class="clear" data-reset="cl">Clear filters</button>' : '') + '<span class="count" id="cnt"></span></div>' +
    '<div class="facets">' +
      facet('cl', 'status', 'Status', CLAIM_ORDER.filter(k => D.claims.some(c => c.status === k)).concat(Object.keys(countBy(D.claims, c => c.status)).filter(k => !CLAIM_ORDER.includes(k))), countBy(D.claims, c => c.status), v => claimPill(v)) +
      facet('cl', 'topic', 'Topic', Object.keys(countBy(D.claims, c => c.topic || 'untagged')).sort(), countBy(D.claims, c => c.topic || 'untagged')) +
      facet('cl', 'agent', 'Agent', Object.keys(countBy(D.claims, c => c._agent)).sort(), countBy(D.claims, c => c._agent)) +
    '</div><div id="list"></div>';
}
function renderClaimList(){
  const rows = filteredClaims(); const el = $('#list'); if (!el) return;
  $('#cnt').textContent = rows.length + ' of ' + D.claims.length;
  if (!rows.length){ el.innerHTML = '<div class="empty">No claim matches.</div>'; return; }
  const g = S.cl.group, key = c => g === 'status' ? c.status : g === 'agent' ? c._agent : (c.topic || 'untagged');
  const groups = {}; rows.forEach(c => (groups[key(c)] = groups[key(c)] || []).push(c));
  const order = Object.keys(groups).sort((a, b) => g === 'status' ? CLAIM_ORDER.indexOf(a) - CLAIM_ORDER.indexOf(b) : (a === 'untagged') - (b === 'untagged') || groups[b].length - groups[a].length);
  el.innerHTML = order.map(k => '<div class="grp-h">' + (g === 'status' ? claimPill(k) : esc(k)) + '<span class="c">' + groups[k].length + '</span></div><div class="list">' + groups[k].map(c => claimHTML(c, S.cl.q)).join('') + '</div>').join('');
}

/* ---------- timeline ---------- */
function filteredEvents(){
  const f = S.tl;
  return D.events.filter(e => (!f.phase || (e.phase || 'unphased') === f.phase) && (!f.conf || e.confidence === f.conf) && (!f.agent || e._agent === f.agent) && matches([e.event, e.note, e.at, (e.sources || []).join(' ')].join(' '), f.q));
}
function vTimeline(){
  const f = S.tl; const any = f.phase || f.conf || f.agent || f.q;
  const phs = PHASES.filter(p => D.events.some(e => e.phase === p)).concat(D.events.some(e => !e.phase) ? ['unphased'] : []);
  return '<div class="vh"><div class="grow"><p class="kicker">Timeline</p><h1>How it unfolded, with every date as it was recorded</h1><p class="lead">A year stays a year and a day stays a day; times are UTC. Stated events come from a source; inferred ones are an agent\'s reading and are drawn with a dashed edge.</p></div></div>' +
    '<div class="toolbar"><div class="fsearch">' + icon('search') + '<input data-q="tl" value="' + attr(f.q) + '" placeholder="Filter events"></div>' + (any ? '<button class="clear" data-reset="tl">Clear filters</button>' : '') + '<span class="count" id="cnt"></span></div>' +
    '<div class="facets">' +
      facet('tl', 'phase', 'Phase', phs, countBy(D.events, e => e.phase || 'unphased'), v => '<span class="ph-dot" style="--pc:' + phaseColor(v) + '"></span>' + esc(v)) +
      facet('tl', 'conf', 'Confidence', Object.keys(countBy(D.events, e => e.confidence)).sort(), countBy(D.events, e => e.confidence)) +
      facet('tl', 'agent', 'Agent', Object.keys(countBy(D.events, e => e._agent)).sort(), countBy(D.events, e => e._agent)) +
    '</div><div id="list"></div>';
}
function renderTimelineList(){
  const rows = filteredEvents(); const el = $('#list'); if (!el) return;
  $('#cnt').textContent = rows.length + ' of ' + D.events.length;
  if (!rows.length){ el.innerHTML = '<div class="empty">No event matches.</div>'; return; }
  const days = []; let cur = null;
  rows.forEach(e => { if (!cur || cur.key !== e._p.day){ cur = {key: e._p.day, label: e._p.dayLabel, rows: []}; days.push(cur); } cur.rows.push(e); });
  const q = S.tl.q;
  el.innerHTML = '<div class="tl">' + days.map(d => '<div class="day"><div class="dl">' + esc(d.label) + '<small>' + plural(d.rows.length, 'event') + '</small></div><div class="evs">' +
    d.rows.map(e => '<div class="ev' + (e.confidence === 'inferred' ? ' inf' : '') + '" id="e-' + attr(e._k) + '" style="--pc:' + phaseColor(e.phase) + '"><div class="when">' + esc(e._p.time || e.at) + '</div><div class="what">' + hl(e.event, q) + '</div>' +
      (e.note ? '<p class="note">' + hl(e.note, q) + '</p>' : '') +
      '<div class="meta">' + (e.phase ? '<span class="ph-dot"></span><span>' + esc(e.phase) + '</span><span>·</span>' : '') + '<span>' + esc(e.confidence || '') + '</span><span>·</span><span class="mono">' + esc(e._agent) + '</span></div>' + srcChips(e.sources) + '</div>').join('') + '</div></div>').join('') + '</div>';
}

/* ---------- desk ---------- */
function deskDocs(){
  const docs = [{id:'readme', title:'The vault protocol', sub:'README.md · how agents write here', kind:'md', text: D.readme}];
  Object.entries(D.memos).sort().forEach(([p, t]) => docs.push({id:p, title: (p.split('__')[2] || p).replace(/\.\w+$/, '').replace(/-/g, ' ').replace(/^./, c => c.toUpperCase()), sub: p.split('/').pop().split('__').slice(0, 2).join(' · ').replace('memo-', 'memo ') + ' · voice memo', kind: /\.md$/.test(p) ? 'md' : 'transcript', text: t}));
  Object.entries(D.deskNotes).sort().forEach(([p, t]) => { const b = p.split('/').pop().replace(/\.md$/, '').split('__'); docs.push({id:p, title:'Working notes: ' + (b[1] || b[0]), sub: (b[0] || '') + ' · ' + p, kind:'md', text: t}); });
  return docs;
}
function vDesk(){
  const docs = deskDocs(); const cur = docs.find(d => d.id === S.desk) || docs[0];
  return '<div class="vh"><div class="grow"><p class="kicker">Desk</p><h1>The editor\'s memos, the agents\' notes and the rules</h1><p class="lead">The brief arrived as voice memos; the agents write a notes file per day. This is the human and agent context behind the evidence.</p></div></div>' +
    '<div class="desk"><div class="docs">' + docs.map(d => '<button class="doc' + (d === cur ? ' on' : '') + '" data-desk="' + attr(d.id) + '"><b>' + esc(d.title) + '</b><span>' + esc(d.sub) + '</span></button>').join('') + '</div>' +
    '<div class="reader">' + (cur.kind === 'transcript' ? transcript(cur.text) : '<div class="md">' + md(cur.text) + '</div>') + '</div></div>';
}

/* ---------- about ---------- */
function vAbout(){
  const v = D.versions || {versions: []};
  const cur = v.current || APP_VERSION;
  return '<div class="vh"><div class="grow"><p class="kicker">About</p><h1>This app, its versions and where the data comes from</h1></div></div>' +
    '<div class="grid g-2"><div class="panel"><h2>Where the data comes from</h2><dl class="kv">' +
      '<dt>Mode</dt><dd>' + (D.mode === 'live' ? '<span class="pill p-good">' + icon('check') + 'live</span> read through the vault bridge when the app opened' : '<span class="pill p-warn">' + icon('help') + 'snapshot</span> the copy inlined at build time (the vault bridge was not available)') + '</dd>' +
      '<dt>Read live</dt><dd class="mono small">sources/index.json, claims/*.json, timeline/*.json, memos/, notes/, sources/&lt;slug&gt;/ on demand</dd>' +
      '<dt>Built</dt><dd>' + esc(D.built || '') + '</dd><dt>Vault head at build</dt><dd class="mono">' + esc(D.head || 'unknown') + '</dd>' +
      '<dt>Snapshot</dt><dd>' + esc((SNAPSHOT || {}).taken_utc || 'none') + ' · ' + plural(((SNAPSHOT || {}).sources || []).length, 'source') + '</dd>' +
      '<dt>Grants</dt><dd><span class="mono">fs.read</span> only. The app writes nothing.</dd></dl>' +
      '<p class="small muted">Screenshots in the app are reduced copies in <span class="mono">app/shots/</span>; they are derived and never evidence. The record is each capture folder, with the sha256 of every file in its <span class="mono">provenance.json</span>, shown in each source\'s panel.</p></div>' +
    '<div class="panel" id="versions"><h2>Versions</h2>' + (v.versions || []).slice().reverse().map(x => '<div style="margin:0 0 12px"><div><span class="pill ' + (x.version === cur ? 'p-good' : 'p-line') + ' mono">' + esc(x.version) + '</span> <span class="small muted">' + esc(x.date || '') + '</span></div><div style="margin-top:4px">' + esc(x.title || '') + '</div>' +
      '<button class="clear" data-ver="' + attr(x.file || '') + '">What changed</button><div class="small" data-verbody="' + attr(x.file || '') + '"></div></div>').join('') + '</div></div>' +
    '<div class="panel sect"><h2>The words</h2><dl class="kv">' + CLAIM_ORDER.map(k => '<dt>' + claimPill(k) + '</dt><dd>' + esc({confirmed:'A primary source shows it.', reported:'A credible party says it; cited, not independently shown.', disputed:'Sources disagree, or the evidence cuts against it.', contradicted:'A primary source says otherwise.', unverified:'Nobody has shown it, including those repeating it.'}[k]) + '</dd>').join('') +
      '<dt>' + srcPill('blocked') + '</dt><dd>Our egress could not reach the page. A limit of our access, never evidence about the source.</dd></dl></div>';
}

/* ---------- source drawer ---------- */
async function openSource(slug){
  const s = D.bySlug[slug]; if (!s) return;
  const caps = (s.captures || []).slice().sort();
  const cc = D.citeC[slug] || [], ce = D.citeE[slug] || [];
  $('#dcr').innerHTML = icon('sources') + ' sources / <span class="mono">' + esc(slug) + '</span>';
  $('#db').innerHTML =
    '<div class="top1" style="display:flex;gap:6px;flex-wrap:wrap"><span class="pill p-kind">' + esc(s.kind) + '</span>' + (s.primary ? '<span class="pill p-prim">' + icon('star') + 'primary</span>' : '') + srcPill(s.status) + '</div>' +
    '<p class="kicker" style="margin-top:12px">' + esc(s.publisher || '') + '</p><h2 class="t">' + esc(s.title || s.url) + '</h2>' +
    '<a href="' + attr(web(s.url)) + '" rel="noopener" class="small" style="overflow-wrap:anywhere">' + esc(s.url) + ' ' + icon('ext') + '</a>' +
    '<dl class="kv"><dt>Published</dt><dd>' + esc(s.published || 'not stated') + '</dd><dt>Captures</dt><dd>' + (caps.length ? plural(caps.length, 'capture') + ', ' + esc(fmtCap(caps[0])) + (caps.length > 1 ? ' to ' + esc(fmtCap(caps[caps.length - 1])) : '') : 'none') + '</dd>' +
    '<dt>Added by</dt><dd class="mono">' + esc(s.added_by || '') + '</dd><dt>Cited by</dt><dd>' + plural(cc.length, 'claim') + ', ' + plural(ce.length, 'timeline event') + '</dd>' + (s.notes ? '<dt>Row note</dt><dd>' + inline(s.notes) + '</dd>' : '') + '</dl>' +
    (caps.length ? '<div class="dsec"><h3>' + icon('camera') + 'Captures</h3><div class="caps">' + caps.map(c => { const sh = (D.shots[slug] || {})[c]; return '<button class="capc" data-cap="' + attr(slug + '|' + c) + '">' + thumbHTML(sh, s) + '<div class="m">' + esc(fmtCap(c)) + '</div></button>'; }).join('') + '</div></div>' : '') +
    '<div class="dsec"><h3>' + icon('text') + 'Notes</h3><div class="md" id="dnotes"><span class="muted small">Reading notes.md…</span></div></div>' +
    (cc.length ? '<div class="dsec"><h3>' + icon('claims') + 'Claims citing it</h3><div class="list">' + cc.map(c => '<div class="claim"><div class="top1">' + claimPill(c.status) + '<button class="clear" style="margin-left:auto" data-claim="' + attr(c._k) + '">In context</button></div><div class="txt" style="font-size:.9rem">' + esc(c.claim) + '</div>' + (c.note ? '<div class="note">' + esc(c.note) + '</div>' : '') + '</div>').join('') + '</div></div>' : '') +
    (ce.length ? '<div class="dsec"><h3>' + icon('timeline') + 'Timeline events citing it</h3><div class="list">' + ce.map(e => '<div class="ev" style="--pc:' + phaseColor(e.phase) + ';margin:0"><div class="when">' + esc(e._p.label) + '</div><div class="what">' + esc(e.event) + '</div><button class="clear" data-event="' + attr(e._k) + '">In context</button></div>').join('') + '</div></div>' : '') +
    '<div class="dsec"><h3>' + icon('file') + 'Files</h3><div id="dfiles"></div></div>' +
    (caps.length ? '<div class="dsec"><h3>' + icon('hash') + 'Provenance</h3><div class="seg" id="dprovsel">' + caps.map((c, i) => '<button data-prov="' + attr(slug + '|' + c) + '" class="' + (i === caps.length - 1 ? 'on' : '') + '">' + esc(fmtCap(c, false).replace(' UTC', '')) + '</button>').join('') + '</div><div id="dprov" style="margin-top:8px"></div></div>' : '');
  openDrawer(); after();
  renderFiles(slug);
  if (caps.length) loadProv(slug, caps[caps.length - 1]);
  const t = await sourceNotes(slug); const n = $('#dnotes'); if (n && $('#dcr').textContent.includes(slug)) n.innerHTML = t ? md(t) : '<span class="muted small">No notes.md for this source.</span>';
}
function renderFiles(slug){
  const rows = D.files[slug] || [];
  const el = $('#dfiles'); if (!el) return;
  if (!rows.length){ el.innerHTML = '<p class="small muted">No file list in the build manifest for this source (added after the last build). The row above comes live from the vault.</p>'; return; }
  const dirs = {}; rows.forEach(([p, sz]) => { const d = p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : ''; (dirs[d] = dirs[d] || []).push([p, sz]); });
  el.innerHTML = '<ul class="files">' + Object.keys(dirs).sort().map(d => (d ? '<li class="dir">' + esc(d) + '/</li>' : '') + dirs[d].map(([p, sz]) => '<li><button data-file="' + attr('sources/' + slug + '/' + p) + '">' + esc(p.split('/').pop()) + '</button><span class="sz">' + fmtBytes(sz) + '</span></li>').join('')).join('') + '</ul>';
}
async function loadProv(slug, cap){
  const el = $('#dprov'); if (!el) return;
  $$('#dprovsel button').forEach(b => b.classList.toggle('on', b.getAttribute('data-prov') === slug + '|' + cap));
  el.innerHTML = '<span class="muted small">Reading provenance.json…</span>';
  let p = null;
  try { p = HAS_SG ? JSON.parse(await sg.vfs.readText('sources/' + slug + '/captures/' + cap + '/provenance.json')) : null; } catch(e){}
  if (!p){ el.innerHTML = '<p class="small muted">' + (HAS_SG ? 'No provenance.json in this capture.' : 'Provenance is read from the vault; open this app inside the vault to see it.') + '</p>'; return; }
  const rows = [['url', p.url], ['final url', p.final_url], ['http status', p.status], ['started', p.started_utc], ['finished', p.finished_utc], ['tool', p.tool], ['user agent', p.user_agent], ['title', p.title], ['note', p.page_html_note]].filter(r => r[1] != null && r[1] !== '');
  const files = Object.entries(p.files || {});
  el.innerHTML = '<div class="prov"><table>' + rows.map(r => '<tr><td>' + esc(r[0]) + '</td><td style="white-space:normal">' + esc(r[1]) + '</td></tr>').join('') +
    files.map(([f, h]) => '<tr><td>sha256 ' + esc(f) + '</td><td>' + esc(h) + '</td></tr>').join('') + '</table></div>';
}
function openDrawer(){ $('#drawer').classList.add('on'); $('#drawer').setAttribute('aria-hidden', 'false'); $('#scrim').classList.add('on'); $('#db').scrollTop = 0; }
function closeDrawer(){ $('#drawer').classList.remove('on'); $('#drawer').setAttribute('aria-hidden', 'true'); $('#scrim').classList.remove('on'); }

/* ---------- files ---------- */
const TEXT_EXT = /\.(txt|md|json|html?|csv|patch|diff|log|xml|js|mjs|py|yml|yaml)$|SHA256SUMS$/i;
async function openFile(path){
  const name = path.split('/').pop();
  if (/\.(png|jpe?g|webp|gif|pdf|mp4|mp3|wav)$/i.test(name)){
    if (HAS_SG && sg.ui && sg.ui.preview){ try { await sg.ui.preview(path); return; } catch(e){ toast('Could not preview ' + name + ': ' + (e.message || e), 'error'); return; } }
    toast('Previews need the vault; open this app inside the vault.', 'warn'); return;
  }
  if (!TEXT_EXT.test(name)){ if (HAS_SG && sg.ui && sg.ui.preview){ try { await sg.ui.preview(path); } catch(e){} } return; }
  $('#trt').innerHTML = icon('file') + ' <span class="mono">' + esc(path) + '</span>';
  $('#trb').innerHTML = '<pre>Reading…</pre>'; $('#trm').classList.add('on');
  let t = null;
  if (HAS_SG){ try { t = await sg.vfs.readText(path); } catch(e){ t = null; } }
  if (t == null){ const m = /^sources\/([^/]+)\/notes\.md$/.exec(path); if (m) t = await sourceNotes(m[1]); }
  if (t == null){ $('#trb').innerHTML = '<pre>This file is read from the vault; open the app inside the vault to read it.</pre>'; return; }
  const big = t.length > 400000; const shown = big ? t.slice(0, 400000) : t;
  let body;
  if (/\.md$/i.test(name)) body = '<div class="md">' + md(shown) + '</div>';
  else if (/\.json$/i.test(name)){ try { body = '<pre>' + esc(JSON.stringify(JSON.parse(t), null, 2).slice(0, 400000)) + '</pre>'; } catch(e){ body = '<pre>' + esc(shown) + '</pre>'; } }
  else body = '<pre>' + esc(shown) + '</pre>';
  $('#trb').innerHTML = (big ? '<div class="small muted" style="padding:8px 18px;border-bottom:1px solid var(--line)">Showing the first 400,000 of ' + t.length.toLocaleString() + ' characters. HTML is shown as source, never rendered.</div>' : (/\.html?$/i.test(name) ? '<div class="small muted" style="padding:8px 18px;border-bottom:1px solid var(--line)">Shown as source, never rendered: captured pages are evidence, not something to run.</div>' : '')) + body;
}
function toast(msg, type){ try { if (HAS_SG && sg.ui && sg.ui.message) { sg.ui.message(msg, type || 'info', {ttl: 4000}); return; } } catch(e){} console.log('[app]', msg); }

/* ---------- viewer ---------- */
let LB = {list: [], i: 0};
function openViewer(slug, cap, list){
  LB.list = list || D.captures.filter(c => c.shot);
  LB.i = Math.max(0, LB.list.findIndex(c => c.slug === slug && c.cap === cap));
  if (!LB.list[LB.i] || LB.list[LB.i].slug !== slug){ const c = D.captures.find(c => c.slug === slug && c.cap === cap); LB.list = [c]; LB.i = 0; }
  renderViewer(); $('#lb').classList.add('on');
}
function renderViewer(){
  const c = LB.list[LB.i]; if (!c) return; const s = D.bySlug[c.slug] || {};
  const base = 'sources/' + c.slug + '/captures/' + c.cap + '/';
  $('#lb').innerHTML = '<div class="stage" id="lbs">' + (c.shot ? '<div class="loading">Loading the page…</div><img alt="' + attr(s.title || '') + '" data-src="' + attr(c.shot.web) + '">' : '<div class="loading">No reduced screenshot for this capture yet. Open the original.</div>') + '</div>' +
    '<div class="info"><div class="nav2"><button class="b2" data-lb="-1" aria-label="Previous">' + icon('left') + '</button><button class="b2" data-lb="1" aria-label="Next">' + icon('right') + '</button><span class="pos">' + (LB.i + 1) + ' / ' + LB.list.length + '</span><button class="b2" data-close="lb" aria-label="Close">' + icon('x') + '</button></div>' +
    '<div class="pub">' + esc(s.publisher || '') + ' · ' + esc(s.kind || '') + (s.primary ? ' · primary' : '') + '</div><h3>' + esc(s.title || c.slug) + '</h3>' +
    '<div class="when">captured ' + esc(fmtCap(c.cap)) + '</div>' +
    (c.shot && c.shot.cut ? '<div class="cut">This view stops at ' + c.shot.wh.toLocaleString() + 'px of a ' + Math.round(c.shot.oh * c.shot.ww / c.shot.ow).toLocaleString() + 'px page; the original has all of it.</div>' : '') +
    '<div class="col"><button class="b2" data-src="' + attr(c.slug) + '">' + icon('sources') + 'Source, notes and citations</button>' +
    '<button class="b2" data-file="' + attr(base + 'screenshot.png') + '">' + icon('expand') + 'Full-resolution original' + (c.shot ? ' (' + c.shot.ow + '×' + c.shot.oh + ')' : '') + '</button>' +
    '<button class="b2" data-file="' + attr(base + 'text.txt') + '">' + icon('text') + 'Page text as captured</button>' +
    '<a class="b2" href="' + attr(web(s.url)) + '" rel="noopener" style="text-decoration:none">' + icon('ext') + 'Live page (it may have changed)</a></div>' +
    '<div class="pub">' + plural(cites(c.slug), 'citation') + ' · ' + plural((s.captures || []).length, 'capture') + ' of this source</div></div>';
  const img = $('#lb img[data-src]');
  if (img){ const p = img.getAttribute('data-src'); img.removeAttribute('data-src'); img.onload = () => { const l = $('#lb .loading'); l && l.remove(); }; img.onerror = () => { const l = $('#lb .loading'); if (l) l.textContent = 'Could not load the reduced screenshot.'; }; img.src = p; }
  $('#lbs').scrollTop = 0;
}
function stepViewer(d){ if (!LB.list.length) return; LB.i = (LB.i + d + LB.list.length) % LB.list.length; renderViewer(); }

/* ---------- global search ---------- */
let SR = {items: [], act: -1};
function runSearch(q){
  const box = $('#sres');
  if (!q.trim()){ box.classList.remove('on'); return; }
  const src = D.sources.filter(s => matches([s.slug, s.title, s.publisher, s.url, s.notes, D.notes[s.slug] || ''].join(' '), q)).slice(0, 7);
  const cl = D.claims.filter(c => matches([c.claim, c.by, c.note, c.id].join(' '), q)).slice(0, 6);
  const ev = D.events.filter(e => matches([e.event, e.note, e.at].join(' '), q)).slice(0, 6);
  SR.items = []; let h = '';
  const add = (title, rows, f) => { if (!rows.length) return; h += '<div class="gh">' + title + '</div>'; rows.forEach(r => { const it = f(r); SR.items.push(it); h += '<button class="r" data-sr="' + (SR.items.length - 1) + '"><b>' + it.t + '</b><span>' + it.s + '</span></button>'; }); };
  add('Sources', src, s => ({t: hl(s.title || s.slug, q), s: esc(pubShort(s)) + ' · ' + esc(s.kind) + ' · ' + esc(s.status), go: () => openSource(s.slug)}));
  add('Claims', cl, c => ({t: hl(c.claim, q), s: esc(c.status) + ' · ' + esc(c.by || ''), go: () => focusClaim(c._k)}));
  add('Timeline', ev, e => ({t: hl(e.event, q), s: esc(e._p.label) + ' · ' + esc(e.phase || ''), go: () => focusEvent(e._k)}));
  box.innerHTML = h || '<div class="none">Nothing in the vault matches “' + esc(q) + '”.</div>';
  SR.act = -1; box.classList.add('on');
}
function pickSearch(i){ const it = SR.items[i]; if (!it) return; $('#sres').classList.remove('on'); $('#q').blur(); it.go(); }
function focusClaim(k){
  closeDrawer(); S.cl = {q:'', status:null, topic:null, agent:null, group:S.cl.group}; go('claims');
  requestAnimationFrame(() => { const el = document.getElementById('c-' + k); if (el){ el.scrollIntoView({block:'center'}); el.classList.add('flash'); } });
}
function focusEvent(k){
  closeDrawer(); S.tl = {q:'', phase:null, conf:null, agent:null}; go('timeline');
  requestAnimationFrame(() => { const el = document.getElementById('e-' + k); if (el){ el.scrollIntoView({block:'center'}); el.classList.add('flash'); } });
}

/* ---------- list re-render after filter changes (keeps focus in the filter box) ---------- */
function renderList(){ ({sources: renderSourceList, wall: renderWallList, claims: renderClaimList, timeline: renderTimelineList}[S.view] || (() => {}))(); }
const _render = render;
render = function(){ _render(); renderList(); };

/* ---------- events ---------- */
document.addEventListener('click', e => {
  const t = e.target.closest('[data-go],[data-src],[data-cap],[data-f],[data-reset],[data-layout],[data-group],[data-order],[data-claim],[data-event],[data-file],[data-prov],[data-close],[data-lb],[data-desk],[data-ver],[data-sr]');
  if (!t) { if (!e.target.closest('.search')) $('#sres').classList.remove('on'); return; }
  const d = t.dataset;
  if (d.sr != null){ pickSearch(+d.sr); return; }
  if (d.close){ if (d.close === 'drawer') closeDrawer(); if (d.close === 'lb') $('#lb').classList.remove('on'); if (d.close === 'text') $('#trm').classList.remove('on'); return; }
  if (d.lb){ stepViewer(+d.lb); return; }
  if (d.cap){ const [slug, cap] = d.cap.split('|'); const inWall = S.view === 'wall' && !t.closest('.drawer'); openViewer(slug, cap, inWall ? wallRows() : null); return; }
  if (d.src){ if ($('#lb').classList.contains('on')) $('#lb').classList.remove('on'); openSource(d.src); return; }
  if (d.file){ openFile(d.file); return; }
  if (d.prov){ const [slug, cap] = d.prov.split('|'); loadProv(slug, cap); return; }
  if (d.claim){ focusClaim(d.claim); return; }
  if (d.event){ focusEvent(d.event); return; }
  if (d.desk){ S.desk = d.desk; render(); return; }
  if (d.ver){ const b = document.querySelector('[data-verbody="' + CSS.escape(d.ver) + '"]'); showVersion(d.ver, b); return; }
  if (d.go){
    let view = d.go, preset = null;
    if (view === 'sources:primary'){ view = 'sources'; preset = {src: {primary: 'true'}}; }
    if (d.preset){ try { preset = JSON.parse(d.preset); } catch(_){} }
    if (preset){ // a preset replaces that view's filters
      const blank = {src:{q:'', kind:null, status:null, primary:null, agent:null}, wall:{q:'', kind:null, bin:null}, cl:{q:'', status:null, topic:null, agent:null}, tl:{q:'', phase:null, conf:null, agent:null}};
      // only the four views' own filters, and only plain values: a preset comes from markup built from vault data,
      // so a key such as __proto__ or a nested object never reaches Object.assign
      for (const k of Object.keys(preset)) {
        if (!Object.prototype.hasOwnProperty.call(blank, k) || !preset[k] || typeof preset[k] !== 'object') continue;
        const clean = {};
        for (const f of Object.keys(blank[k])) { const v = preset[k][f]; if (Object.prototype.hasOwnProperty.call(preset[k], f) && (v === null || typeof v === 'string')) clean[f] = v; }
        Object.assign(S[k], blank[k], clean);
      }
    }
    closeDrawer(); go(view); return;
  }
  if (d.f){ const [g, k, ...rest] = d.f.split(':'); const v = rest.join(':'); S[g][k] = S[g][k] === v ? null : v; render(); return; }
  if (d.reset){ const g = d.reset; const keep = {src:['sort','layout'], wall:['order'], cl:['group'], tl:[]}[g]; for (const k of Object.keys(S[g])) if (!keep.includes(k)) S[g][k] = k === 'q' ? '' : null; render(); return; }
  if (d.layout){ S.src.layout = d.layout; persist(); render(); return; }
  if (d.group){ S.cl.group = d.group; persist(); render(); return; }
  if (d.order){ S.wall.order = d.order; persist(); render(); return; }
}, false);
document.addEventListener('input', e => {
  const t = e.target;
  if (t.id === 'q'){ runSearch(t.value); return; }
  if (t.dataset && t.dataset.q){ S[t.dataset.q].q = t.value; renderList(); }
});
document.addEventListener('change', e => { const t = e.target; if (t.dataset && t.dataset.sort){ S.src.sort = t.value; renderList(); } });
document.addEventListener('keydown', e => {
  const inField = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || '');
  if (e.key === 'Escape'){
    if ($('#trm').classList.contains('on')) $('#trm').classList.remove('on');
    else if ($('#lb').classList.contains('on')) $('#lb').classList.remove('on');
    else if ($('#drawer').classList.contains('on')) closeDrawer();
    else if ($('#sres').classList.contains('on')){ $('#sres').classList.remove('on'); $('#q').blur(); }
    return;
  }
  if ($('#lb').classList.contains('on') && !inField){ if (e.key === 'ArrowLeft'){ stepViewer(-1); e.preventDefault(); } if (e.key === 'ArrowRight'){ stepViewer(1); e.preventDefault(); } return; }
  if (e.target.id === 'q' && $('#sres').classList.contains('on')){
    const n = SR.items.length;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){ e.preventDefault(); SR.act = (SR.act + (e.key === 'ArrowDown' ? 1 : -1) + n) % n; $$('#sres .r').forEach((b, i) => b.classList.toggle('act', i === SR.act)); const a = $('#sres .r.act'); a && a.scrollIntoView({block:'nearest'}); }
    if (e.key === 'Enter'){ e.preventDefault(); pickSearch(SR.act < 0 ? 0 : SR.act); }
    return;
  }
  if (!inField && (e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'))){ e.preventDefault(); $('#q').focus(); $('#q').select(); }
});
$('#scrim').addEventListener('click', closeDrawer);
$('#trm').addEventListener('click', e => { if (e.target.id === 'trm') $('#trm').classList.remove('on'); });
$('#q').addEventListener('focus', e => { if (e.target.value) runSearch(e.target.value); });
$('#theme').addEventListener('click', () => { const dark = S.theme ? S.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; setTheme(dark ? 'light' : 'dark'); persist(); });

async function showVersion(file, el){
  if (!el || !file) return;
  if (el.innerHTML){ el.innerHTML = ''; return; }
  let v = null;
  if (HAS_SG){ try { v = JSON.parse(await sg.vfs.readText('app/versions/' + file)); } catch(e){} }
  if (!v){ v = ((SNAPSHOT || {}).version_files || {})[file] || null; }
  el.innerHTML = v ? '<ul>' + (v.changes || []).map(x => '<li>' + inline(x) + '</li>').join('') + '</ul>' + (v.vault_head_at_build ? '<div class="muted">built on vault head <span class="mono">' + esc(v.vault_head_at_build) + '</span>' + (v.built_utc ? ' at ' + esc(v.built_utc) : '') + '</div>' : '') : '<span class="muted">Read from app/versions/' + esc(file) + ' inside the vault.</span>';
}

/* ---------- boot ---------- */
(async function boot(){
  try {
    setTheme(null);
    $$('[data-close]').forEach(b => { if (!b.innerHTML.trim()) b.innerHTML = icon('x'); });
    if (SNAPSHOT){ ingest(SNAPSHOT); D.taken = SNAPSHOT.taken_utc; }
    const ui = await store.get('ui');
    if (ui){ if (ui.theme) setTheme(ui.theme); if (ui.layout) S.src.layout = ui.layout; if (ui.group) S.cl.group = ui.group; if (ui.order) S.wall.order = ui.order; if (ui.view && VIEWS.some(v => v[0] === ui.view)) S.view = ui.view; }
    renderSide(); render(); ready();
    if (HAS_SG){
      try { if (await loadLive()){ renderSide(); const keepScroll = $('#main').scrollTop; render(); $('#main').scrollTop = keepScroll; } }
      catch(e){ console.warn('[app] live read failed; showing the snapshot', e); toast('Showing the snapshot built ' + (D.taken || '') + ': the live read failed.', 'warn'); }
    }
  } catch(err){
    console.error('[app] boot failed', err);
    $('#main').innerHTML = '<div class="wrap"><div class="empty">The app could not start: ' + esc(err && err.message || err) + '</div></div>';
    ready();
  }
})();
</script>
</body>
</html>
