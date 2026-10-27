/* The days mock-up's content (story-site, 27 October 2026): eight days of the php2shell story, written for the mock-up
   from the newsroom's own records (data's state.json versions v0 to v3, sources.json by published date, timeline.json,
   compromise.json, impact.json, and the breaking brief BREAKING-001). In the real thing each day is a data file the desk
   writes and a renderer draws; here it is one file so the mock-up can be read on its own.

   A day is a calendar day in UTC. An item belongs to the day it happened, with the time the newsroom learned it when that
   is later ("learned"). Each item names the roles it is news for; a role with no item on a day is told so, plainly. */
window.DAYS = {
  now: '2026-10-27T09:10Z',
  roles: {
    exec: { name: 'Executive', as: 'an Executive' },
    general: { name: 'General reader', as: 'a general reader' },
    security: { name: 'Security', as: 'Security' },
    engineer: { name: 'Engineer', as: 'an Engineer' },
    journalist: { name: 'Journalist', as: 'a Journalist' },
    researcher: { name: 'Researcher', as: 'a Researcher' },
    everything: { name: 'Everything', as: 'everything' }
  },
  order: ['exec', 'general', 'security', 'engineer', 'journalist', 'researcher', 'everything'],

  /* The measures every day ends on: the five a reader asks first. Values per day; a value equal to the day before is
     drawn as unchanged. */
  measures: [
    { id: 'fix', q: 'Is there a fix?' },
    { id: 'exploited', q: 'Exploited, per CISA?' },
    { id: 'hacked', q: 'Anyone confirmed hacked?' },
    { id: 'offline', q: 'Sites taken offline' },
    { id: 'unpatched', q: 'Still unpatched' }
  ],

  days: [
    {
      n: 0, date: '2026-10-20', label: 'The warning',
      size: 'small', coverage: 4,
      headline: {
        _: 'PHP warns of two emergency fixes for tomorrow, and the details leak a day early.',
        engineer: 'Two critical PHP fixes announced for tomorrow; no versions or patches yet.',
        journalist: 'The disclosure leaks: The Hacker News names "PHP2Shell" before any fix exists.'
      },
      state: { fix: 'Not yet', exploited: 'Not listed', hacked: 'None', offline: 'None', unpatched: 'Everyone' },
      items: [
        { t: '15:00', tag: 'New', text: 'PHP announces two critical security releases for the next day, on the oss-security list.', roles: ['security', 'engineer', 'researcher', 'everything'], src: 'oss-security' },
        { t: '20:22', tag: 'New', text: 'The Hacker News publishes "Two unpatched critical PHP RCE flaws", a day before the fix: the coordinated disclosure has broken.', roles: ['journalist', 'researcher', 'security', 'everything'], src: 'The Hacker News' },
        { t: '23:00', tag: 'New', text: 'Ars Technica: PHP warns it plans two emergency patches imminently.', roles: ['exec', 'general', 'journalist', 'everything'], src: 'Ars Technica' }
      ]
    },
    {
      n: 1, date: '2026-10-21', label: 'The fix',
      size: 'huge', coverage: 135,
      headline: {
        _: 'Two critical flaws in PHP are fixed. Governments say install it now, or take sites offline if you cannot.',
        exec: 'Fixed today. Every agency says update first; the US says take systems offline if you cannot. Decide who makes that call.',
        general: 'A fix for websites, not for your phone or laptop. Sites you use may go offline for a while.',
        security: 'Patch internet-facing mod_php first, then FPM. The US says take unpatchable systems offline.',
        engineer: 'Target 8.5.12, 8.4.27, 8.3.36 or 8.2.35, and restart every worker.',
        journalist: 'Fix released 21 October, 14:06 UTC. "70% of the Internet" is a share of websites, not of the Internet.',
        researcher: 'Two CVEs, CVSS 4.0 9.2 from the CNA; two bug classes in the engine; the fix is public in php-src.'
      },
      state: { fix: 'Yes', exploited: 'Not listed', hacked: 'None', offline: 'Governments in Latvia, the Netherlands, France', unpatched: 'Most of 1.6 million hosts' },
      items: [
        { t: '14:06', tag: 'New', text: 'PHP 8.5.12, 8.4.27, 8.3.36 and 8.2.35 released: both flaws fixed.', roles: ['exec', 'general', 'security', 'engineer', 'journalist', 'researcher', 'everything'], src: 'php.net, GitHub', big: true },
        { t: '14:17', tag: 'New', text: 'NVD publishes CVE-2026-109618 and CVE-2026-109619 with the CNA\'s score, 9.2; no NIST score yet.', roles: ['security', 'engineer', 'researcher', 'everything'], src: 'NVD' },
        { t: '14:34', tag: 'New', text: 'CISA, NSA and the UK NCSC: install the fix now; if you cannot, take the system offline.', roles: ['exec', 'general', 'security', 'journalist', 'everything'], src: 'CISA, NSA, NCSC', big: true },
        { t: '15:24', tag: 'New', text: 'A report on oss-security says the 8.5.12 fix may be incomplete; unconfirmed.', roles: ['security', 'engineer', 'researcher', 'everything'], src: 'oss-security' },
        { t: '18:20', tag: 'New', text: 'Latvia restricts state websites from abroad; Dutch and French government sites go offline as a precaution.', roles: ['exec', 'general', 'journalist', 'everything'], src: 'CERT.LV, NCSC-NL, ANSSI' },
        { t: '20:15', tag: 'New', text: 'New Zealand\'s NCSC is "aware of reports of active exploitation"; Huntress sees none on its partners\' systems.', roles: ['security', 'journalist', 'researcher', 'everything'], src: 'NCSC NZ, Huntress' }
      ]
    },
    {
      n: 2, date: '2026-10-22', label: 'The world notices',
      size: 'big', coverage: 143,
      headline: {
        _: 'The story goes worldwide: 143 articles, sites dark in a dozen countries, millions of attack attempts, and still no confirmed break-in.',
        exec: 'Millions of attempts, no confirmed break-in. Your three questions: do we know every PHP system, is it patched and restarted, who can pull it offline?',
        security: 'Cloudflare counts millions of attempts after disclosure; 586 public proof-of-concept repositories by evening.',
        engineer: 'Backports imply versions down to 7.4 are affected, whatever the subject line says.',
        journalist: 'Coverage peaks (143 articles). "Millions" are attempts, not intrusions; no organisation says it was breached.'
      },
      state: { fix: 'Yes', exploited: 'Not listed', hacked: 'None', offline: '10 operators reported', unpatched: 'Most of 1.6 million hosts' },
      items: [
        { t: '01:25', tag: 'New', text: 'Cloudflare\'s CEO: thousands of attempts before disclosure, millions after.', roles: ['exec', 'security', 'journalist', 'everything'], src: 'Cloudflare' },
        { t: '06:16', tag: 'New', text: 'BBC opens a live page: "Global scramble to fix critical cyber-security flaws as many websites taken offline".', roles: ['general', 'journalist', 'everything'], src: 'BBC' },
        { t: '06:45', tag: 'New', text: 'Greenbone: the backports imply versions down to 7.4 are affected.', roles: ['engineer', 'security', 'researcher', 'everything'], src: 'oss-security' },
        { t: '08:40', tag: 'New', text: 'The Dutch NCSC\'s inventory lists 674 products: 46 known affected, 418 not yet assessed.', roles: ['security', 'engineer', 'exec', 'everything'], src: 'NCSC-NL' },
        { t: '11:34', tag: 'New', text: 'This site opens: 391 pages by evening, every fact linked to a saved copy of its source.', roles: ['everything'], src: 'the newsroom' },
        { t: '17:51', tag: 'New', text: '586 public php2shell repositories on GitHub; most are scanners, some are working exploits.', roles: ['security', 'researcher', 'everything'], src: 'GitHub search' }
      ]
    },
    {
      n: 3, date: '2026-10-23', label: 'The count',
      size: 'big', coverage: 55,
      headline: {
        _: 'NIST rates it 9.8; sites come back online; one claimed break-in is withdrawn.',
        exec: 'One claimed break-in was withdrawn. Still no organisation says it was hit. 50 of 51 sites that went dark are back.',
        security: 'NVD: CVSS 3.1 9.8. 735 public repositories. Vendors: 10 of their products vulnerable, 26 not, 16 still being checked.',
        engineer: 'The inventory grows to 751 products; 389 not yet assessed. Check bought-in software, not only your own servers.',
        journalist: 'Sophos withdraws its claimed compromise: don\'t report a confirmed break-in. 3 candidate incidents, none linked yet.',
        general: 'Most websites that went offline are back. Nothing has been taken from people that anyone knows of.'
      },
      state: { fix: 'Yes', exploited: 'Not listed', hacked: 'None (3 candidates)', offline: '51 listed, 50 back', unpatched: 'Switzerland: 3.5% a day after' },
      items: [
        { t: '01:20', tag: 'Changed', text: 'Sites taken offline: 10 reported becomes 51 listed, 50 back online, 1 still dark.', before: '10 operators reported', after: '51 listed, 50 back', roles: ['exec', 'general', 'journalist', 'everything'], src: 'phpocalypse tracker' },
        { t: '01:20', tag: 'New', text: 'Three incidents are named as possibly linked (Czech university, two Japanese firms); none confirmed.', roles: ['exec', 'journalist', 'researcher', 'everything'], src: 'Lupa, Yahoo Japan, Sankei' },
        { t: '08:03', tag: 'Changed', text: 'NIST scores both flaws CVSS 3.1 9.8, beside the CNA\'s 9.2.', before: 'no NIST score', after: '9.8', roles: ['security', 'engineer', 'researcher', 'everything'], src: 'NVD' },
        { t: '12:50', tag: 'Changed', text: 'The Dutch inventory: 109 of 751 products known affected.', before: '46 of 674', after: '109 of 751', roles: ['security', 'engineer', 'everything'], src: 'NCSC-NL' },
        { t: '16:04', tag: 'Corrected', text: 'Sophos withdraws its claim of a successful compromise.', roles: ['exec', 'security', 'journalist', 'everything'], src: 'Sophos, via Cybersecurity News', big: true },
        { t: '16:04', tag: 'New', text: 'Switzerland: just over 23,000 of nearly 690,000 servers still affected a day after the fix.', roles: ['security', 'journalist', 'everything'], src: 'ICTjournal' }
      ]
    },
    {
      n: 4, date: '2026-10-24', label: 'Saturday',
      size: 'small', coverage: 13,
      headline: {
        _: 'A quiet Saturday. One agency joins those seeing no exploitation; a report of state-linked preparation is not confirmed.',
        exec: 'Nothing changes what you should decide today.',
        security: 'Korean press reports a North Korea-linked group preparing attacks; no indicators published, not confirmed.',
        journalist: 'The Lazarus angle (Korean press) has no named source; NPR runs the "AI found it, hackers found the leak" story.'
      },
      state: { fix: 'Yes', exploited: 'Not listed', hacked: 'None (3 candidates)', offline: '51 listed, 50 back', unpatched: 'Switzerland: 3.5% a day after' },
      items: [
        { t: '08:37', tag: 'New', text: 'The Netherlands joins the agencies that have seen no exploitation: six now.', roles: ['security', 'journalist', 'everything'], src: 'NCSC-NL' },
        { t: '09:10', tag: 'New', text: 'Korean newspapers report a North Korea-linked group preparing attacks on government and finance; no indicators, no named source.', roles: ['security', 'journalist', 'researcher', 'everything'], src: 'Hankyung, Money Today' },
        { t: '14:00', tag: 'New', text: 'NPR: "AI found the flaw. Hackers found the leak."', roles: ['general', 'journalist', 'everything'], src: 'NPR' }
      ]
    },
    {
      n: 5, date: '2026-10-25', label: 'Sunday',
      size: 'quiet', coverage: 11,
      headline: {
        _: 'Quiet. Italy\'s agency says only 18% of its PHP services are updated.',
        exec: 'Nothing new for you. Italy\'s figure is a reminder: most systems out there are still unpatched.',
        security: 'Italy\'s ACN: 81.9% of PHP services still vulnerable. India: 14% impact rate, above the global average.'
      },
      state: { fix: 'Yes', exploited: 'Not listed', hacked: 'None (3 candidates)', offline: '51 listed, 50 back', unpatched: 'Italy: 81.9% of services' },
      items: [
        { t: '10:00', tag: 'Changed', text: 'Italy\'s ACN: only 18% of PHP services updated; 81.9% still vulnerable.', before: 'Switzerland: 3.5% a day after', after: 'Italy: 81.9% of services', roles: ['security', 'journalist', 'everything'], src: 'ACN, via Matrice Digitale' },
        { t: '12:00', tag: 'New', text: 'India records a 14% impact rate, above the global average.', roles: ['security', 'everything'], src: 'CIOL' }
      ]
    },
    {
      n: 6, date: '2026-10-26', label: 'CISA lists it',
      size: 'big', coverage: 21,
      headline: {
        _: 'Late in the day, CISA adds both flaws to its list of vulnerabilities known to be exploited. No victim is named.',
        exec: 'CISA now says both flaws are exploited. No organisation says it was hit. US agencies must patch by 29 October; so should you.',
        general: 'The US government now says criminals are using these flaws. If someone runs your website, ask them if it is updated.',
        security: 'KEV: both CVEs added 26 October, due 29 October, ransomware use "Unknown". Treat as exploited; hunt as well as patch.',
        engineer: 'Nothing new to install. Exploited is now official: confirm the fixed version is what is running, after the restart.',
        journalist: '"Exploited" is now CISA\'s word, from 26 October. "Hacked" is not: no named victim. Keep the two apart.',
        researcher: 'KEV catalogue 2026.10.26 lists both; the evidence behind the listing is not public.'
      },
      state: { fix: 'Yes', exploited: '2 of 2, from 26 Oct', hacked: 'None (3 candidates)', offline: '51 listed, 50 back', unpatched: 'Italy: 81.9% of services' },
      items: [
        { t: '09:00', tag: 'New', text: 'Extended support vendors ship the fix for out-of-support PHP 5.3 to 8.1.', roles: ['engineer', 'security', 'everything'], src: 'PR TIMES, @Press' },
        { t: '11:00', tag: 'New', text: 'CPO Magazine: a threat actor targeted PHP flaws days before the disclosure.', roles: ['security', 'researcher', 'journalist', 'everything'], src: 'CPO Magazine' },
        { t: '14:00', tag: 'Still', text: 'A newspaper reports attempts in the millions but no successful code execution in the investigations it cites.', roles: ['exec', 'journalist', 'everything'], src: 'compromise ledger' },
        { t: '22:24', learned: '27 Oct, 00:45', tag: 'Changed', text: 'CISA adds both CVEs to its Known Exploited Vulnerabilities catalogue: added 26 October, due 29 October, ransomware use unknown.', before: 'Not listed', after: '2 of 2', roles: ['exec', 'general', 'security', 'engineer', 'journalist', 'researcher', 'everything'], src: 'CISA KEV 2026.10.26', big: true }
      ]
    },
    {
      n: 7, date: '2026-10-27', label: 'Today', today: true,
      size: 'small', coverage: 0,
      headline: {
        _: 'So far today: the newsroom checks every page that said "not exploited", and keeps "no confirmed break-in" as its own line.',
        exec: 'Nothing new since last night\'s listing. The deadline to ask your team: 29 October.',
        journalist: 'Our pages that said "not on CISA\'s list" are being corrected, each with the date it changed.'
      },
      state: { fix: 'Yes', exploited: '2 of 2, from 26 Oct', hacked: 'None (3 candidates)', offline: '51 listed, 50 back', unpatched: 'Italy: 81.9% of services' },
      items: [
        { t: '01:30', tag: 'New', text: 'The newsroom opens BREAKING-001: every page and record that the listing touches is checked and dated.', roles: ['journalist', 'researcher', 'everything'], src: 'the newsroom' },
        { t: '06:40', tag: 'Still', text: '"Has any organisation confirmed a compromise through php2shell?" Still no, as of the latest capture.', roles: ['exec', 'general', 'journalist', 'everything'], src: 'compromise ledger' }
      ]
    }
  ]
};
