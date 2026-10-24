ROVOR DIGITAL — EXACT REFERENCE HUD
===================================

Open index.html in a modern browser. The original 1672x941-pixel reference image is used unchanged as the screen artwork. Buttons/hotspots are HTML overlays aligned to the source image, not pixels painted into a noninteractive preview.

Controls:
  Click ACTIVE TASKS / RESOURCE USAGE / RECENT ACTIVITY / SYSTEM HEALTH / API QUOTA / LIVE FEED.
  Click the central ROVOR logo to open the command menu.
  Click the bottom DASHBOARD / TASKS / MEDIA / GITHUB / SETTINGS dock.
  Ctrl+K or Cmd+K = search commands. 1-5 = navigation. Escape = close.
  Click 1:1 in the top toolbar or press I to enter or leave the edge-to-edge original image mode.
  Settings can switch between the exact source artwork and optional blue-only recolored art.

LIVE DATA SAFETY:
  Static screenshot labels such as 99%, RUNNING, API quota, and camera are example artwork.
  They are NOT live status. An always-visible utility label explains this unless immersive
  mode is explicitly selected. Open a panel to see source-verified data instead.
  The inspector fetches one GitHub commit and pins task queue + routing map to that SHA;
  it never assumes ownership implies a live Mac process. No credentials, privileged
  commands, or paid APIs are used. If GitHub cannot be reached, status is UNVERIFIED.

REQUIREMENTS:
  Browser: Chrome/Edge/Safari/Firefox with JavaScript enabled.
  Internet for live GitHub status; visual HUD itself works completely offline.
  On Mac, for best live GitHub access, host the directory from a local static web server.
  example: python3 -m http.server 8080  (run inside the project folder)
  then open http://localhost:8080

Files:
  index.html           main interactive HUD
  style.css            styling and responsive behavior
  app.js               interactions and verified data fetch
  reference.png        EXACT unchanged 1672x941 artwork
  reference-blue.webp  optional green-free recoloring

No invented live source information. The demo artwork is accurately labeled as such.

QUICK START ON MAC:
  1) Unzip ROVOR_HUD_Exact_Project.zip.
  2) Double-click Start ROVOR HUD.command (or open it via right-click > Open).
  3) The HUD opens at http://127.0.0.1:8765/.
  4) Choose the "1:1" top toolbar option to hide all extra controls and see the
     unchanged reference pixels, or press I. Use Esc/I to exit immersive mode.

GITHUB PAGES EXACT BUILD:
  The exact PNG artwork is the unchanged visual source, sized 1672 x 941.
  Desktop widescreen loads directly into cinematic view; press I to show the
  toolbar or Esc to exit cinematic view. Clicking the central emblem opens
  the interactive command console in either display mode.
  `service-worker.js` is scoped to this exact HUD subdirectory and only caches
  same-origin static assets; it never caches authenticated/private requests,
  GitHub API endpoints, task queue or routing responses.
  `manifest.webmanifest` makes this site installable in supported browsers.

SAFE OPERATION:
  Nothing in this package starts a worker, publishes social posts, accesses
  a Mac, or spends API credits. GitHub status is verified through one SHA;
  the static example numbers remain illustrative imagery only.
