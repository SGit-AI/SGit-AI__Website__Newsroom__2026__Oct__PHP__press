<div class="root" part="root">
    <div class="bar" data-role="bar" role="toolbar" aria-label="Graph controls">
        <input class="find" data-role="find" type="search" placeholder="Find a node" aria-label="Find a node by name" autocomplete="off">
        <span class="views" role="group" aria-label="How to draw it">
            <button type="button" data-view="ego" aria-pressed="false">Around one</button>
            <button type="button" data-view="layers" aria-pressed="false">In layers</button>
            <button type="button" data-view="map" aria-pressed="false">Map</button>
            <button type="button" data-view="list" aria-pressed="false">List</button>
        </span>
        <label class="depth">Depth <select data-role="depth" aria-label="How many hops from the node in focus"><option>1</option><option>2</option><option>3</option></select></label>
    </div>
    <div class="hits" data-role="hits" role="group" aria-label="Matching nodes" hidden></div>
    <nav class="trail" data-role="trail" aria-label="The path you walked"></nav>
    <div class="chips" data-role="chips" role="group" aria-label="Show only these verbs"></div>
    <div class="stage" data-role="stage"></div>
    <div class="detail" data-role="detail" aria-live="polite"></div>
    <div class="list" data-role="list"></div>
    <p class="foot" data-role="foot"></p>
</div>
