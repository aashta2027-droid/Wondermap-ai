 import json

MAP_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<style>
  html, body { margin: 0; padding: 0; height: 100%; font-family: Arial, sans-serif; }
  #wrap { position: relative; height: 100%; }
  #map { position: absolute; inset: 0; }
  #top { position: absolute; top: 0; left: 0; right: 0; z-index: 500; background: #1b7a4b; padding: 6px 8px; }
  #search { width: 100%; padding: 8px; border: 0; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
  #filters { display: flex; gap: 6px; overflow-x: auto; padding-top: 6px; }
  .chip { flex: 0 0 auto; padding: 5px 10px; border-radius: 14px; background: #fff; color: #1b7a4b; font-size: 12px; border: 0; }
  .chip.active { background: #ffd54f; color: #000; font-weight: bold; }
  .emoji-marker { font-size: 26px; line-height: 30px; text-align: center; }
  .pop { font-size: 13px; color: #111; line-height: 1.35; }
  .pop h4 { margin: 0 0 2px 0; font-size: 15px; }
  .pop .note { margin-top: 6px; font-size: 11px; color: #777; }
</style>
</head>
<body>
<div id="wrap">
  <div id="map"></div>
  <div id="top">
    <input id="search" type="text" placeholder="Search places, cafes, hotels, beaches..."/>
    <div id="filters"></div>
  </div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
(function () {
  var places = __PLACES__;
  var focusId = __FOCUS__;
  var map = L.map('map', { zoomControl: false }).setView([11.6765, 92.7275], 9);
  L.control.zoom({ position: 'bottomleft' }).addTo(map);

  var street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' });
  var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 19, maxNativeZoom: 17, attribution: 'Imagery &copy; Esri and contributors' });
  var terrain = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    { maxZoom: 19, maxNativeZoom: 17,
      attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Style: &copy; OpenTopoMap (CC-BY-SA)' });
  street.addTo(map);
  L.control.layers({ 'Street': street, 'Satellite': satellite, 'Terrain': terrain }, null,
    { position: 'bottomright' }).addTo(map);

  var cluster = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 45 });
  map.addLayer(cluster);

  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function row(l, v) {
    if (!v || String(v).indexOf('Not confirmed') === 0) { return ''; }
    return '<div><b style="color:#1b7a4b">' + l + ':</b> ' + esc(v) + '</div>';
  }

  var markers = {};
  var activeCat = 'All Places';

  function popupHtml(p) {
    var note = 'Details can change. Please confirm locally.';
    if (p.source === 'community') { note = 'Community-submitted place, approved by the owner. Not officially verified.'; }
    if (p.source === 'osm') { note = 'From OpenStreetMap volunteers. Not verified.'; }
    var link = 'https://www.google.com/maps/search/?api=1&query=' + Number(p.lat) + ',' + Number(p.lng);
    return '<div class="pop"><h4>' + esc(p.emoji) + ' ' + esc(p.name) + '</h4>' +
      '<div style="color:#555;margin-bottom:6px">' + esc(p.category) + ' · ' + esc(p.area) + '</div>' +
      '<div>' + esc(p.info) + '</div>' +
      row('Hours', p.hours) + row('Cost', p.fee) + row('Best time', p.best_time) + row('Tips', p.tips) +
      '<div style="margin-top:6px"><a href="' + link + '" target="_blank" rel="noopener">Open in Google Maps</a></div>' +
      '<div class="note">' + note + '</div></div>';
  }

  places.forEach(function (p) {
    var icon = L.divIcon({ className: '', html: '<div class="emoji-marker">' + esc(p.emoji) + '</div>', iconSize: [30, 30], iconAnchor: [15, 15] });
    var m = L.marker([p.lat, p.lng], { icon: icon });
    m.bindPopup(function () { return popupHtml(p); }, { maxWidth: 250, maxHeight: 320 });
    markers[p.id] = m;
  });

  function applyFilters() {
    var q = document.getElementById('search').value.toLowerCase().trim();
    var list = [];
    places.forEach(function (p) {
      var okCat = activeCat === 'All Places' || p.category === activeCat;
      var text = (p.name + ' ' + p.category + ' ' + p.area).toLowerCase();
      var okTxt = !q || text.indexOf(q) > -1;
      if (okCat && okTxt) { list.push(markers[p.id]); }
    });
    cluster.clearLayers();
    cluster.addLayers(list);
  }

  var cats = ['All Places'];
  places.forEach(function (p) { if (cats.indexOf(p.category) < 0) cats.push(p.category); });
  var fbox = document.getElementById('filters');
  cats.forEach(function (c) {
    var b = document.createElement('button');
    b.className = 'chip' + (c === activeCat ? ' active' : '');
    b.textContent = c;
    b.onclick = function () {
      activeCat = c;
      Array.prototype.forEach.call(fbox.children, function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      applyFilters();
    };
    fbox.appendChild(b);
  });
  document.getElementById('search').addEventListener('input', applyFilters);
  applyFilters();

  if (focusId && markers[focusId] && cluster.hasLayer(markers[focusId])) {
    var f = places.filter(function (p) { return p.id === focusId; })[0];
    map.setView([f.lat, f.lng], 13);
    cluster.zoomToShowLayer(markers[focusId], function () { markers[focusId].openPopup(); });
  }
})();
</script>
</body>
</html>
"""


def slim(p):
    d = {k: p[k] for k in ("id", "name", "category", "emoji", "lat", "lng", "area", "source", "info")}
    if p["source"] != "osm":
        for k in ("hours", "fee", "best_time", "tips"):
            d[k] = p[k]
    elif not str(p["hours"]).startswith("Not confirmed"):
        d["hours"] = p["hours"]
    return d


def build_map_html(places, focus=""):
    data = json.dumps([slim(p) for p in places], ensure_ascii=False).replace("</", "<\\/")
    return (MAP_TEMPLATE
            .replace("__PLACES__", data)
            .replace("__FOCUS__", json.dumps(focus or "")))
# END OF FILE
