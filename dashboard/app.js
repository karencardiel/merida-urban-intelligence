/**
 * Mérida Urban Intelligence — Geospatial Dashboard Client Logic
 * Uses CartoDB dark_nolabels as the base map, with block boundaries and street labels.
 */

// Global State
let map;
let blocksLayer;
let markersLayer;
let heatLayer;
let labelsLayer;

// Color Palette for Risk Levels (Blocks)
const RISK_COLORS = {
  'Crítico (Punto Rojo)': '#f43f5e',
  'Alto': '#f97316',
  'Moderado': '#eab308',
  'Bajo': '#06b6d4'
};

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initLayerToggles();
  initFilters();
  renderBlocksLayer();
  renderMarkersLayer();
  updateKpis();
});

function initMap() {
  // Center on Mérida (Plaza Grande)
  map = L.map('map', {
    center: [20.9673, -89.6237],
    zoom: 14,
    minZoom: 11,
    maxZoom: 19,
    zoomControl: false
  });

  L.control.zoom({ position: 'topright' }).addTo(map);

  // 1. Base Layer: CartoDB Dark No Labels (Requested Configuration)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
  }).addTo(map);

  // 2. Dedicated Top Pane for Street Labels (Renders street names ON TOP of block polygons)
  map.createPane('labelsPane');
  map.getPane('labelsPane').style.zIndex = 650;
  map.getPane('labelsPane').style.pointerEvents = 'none'; // Clicks pass through to blocks

  labelsLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 19,
    pane: 'labelsPane'
  }).addTo(map);

  // Layer containers (Rendered in middle between base and labels)
  blocksLayer = L.layerGroup().addTo(map);
  markersLayer = L.layerGroup().addTo(map);
}

function initLayerToggles() {
  const chkBlocks = document.getElementById('chk-blocks');
  const chkMarkers = document.getElementById('chk-markers');
  const chkHeatmap = document.getElementById('chk-heatmap');
  const chkLabels = document.getElementById('chk-labels');

  if (chkBlocks) {
    chkBlocks.addEventListener('change', (e) => {
      if (e.target.checked) map.addLayer(blocksLayer);
      else map.removeLayer(blocksLayer);
    });
  }

  if (chkMarkers) {
    chkMarkers.addEventListener('change', (e) => {
      if (e.target.checked) map.addLayer(markersLayer);
      else map.removeLayer(markersLayer);
    });
  }

  if (chkHeatmap) {
    chkHeatmap.addEventListener('change', (e) => {
      if (e.target.checked) {
        if (!heatLayer) initHeatLayer();
        map.addLayer(heatLayer);
      } else {
        if (heatLayer) map.removeLayer(heatLayer);
      }
    });
  }

  if (chkLabels) {
    chkLabels.addEventListener('change', (e) => {
      if (e.target.checked) map.addLayer(labelsLayer);
      else map.removeLayer(labelsLayer);
    });
  }
}

function initFilters() {
  const filterRisk = document.getElementById('filter-risk');
  const filterType = document.getElementById('filter-type');

  if (filterRisk) {
    filterRisk.addEventListener('change', () => {
      renderBlocksLayer();
    });
  }

  if (filterType) {
    filterType.addEventListener('change', () => {
      renderMarkersLayer();
      if (heatLayer && map.hasLayer(heatLayer)) {
        map.removeLayer(heatLayer);
        initHeatLayer();
        map.addLayer(heatLayer);
      }
    });
  }
}

/**
 * Render Explicit Block Boundaries (Manzanas)
 */
function renderBlocksLayer() {
  blocksLayer.clearLayers();

  if (typeof BLOCKS_GEOJSON === 'undefined') {
    console.error("BLOCKS_GEOJSON not loaded.");
    return;
  }

  const riskFilter = document.getElementById('filter-risk') ? document.getElementById('filter-risk').value : 'ALL';

  const filteredFeatures = BLOCKS_GEOJSON.features.filter(feat => {
    const total = feat.properties.total_incidents;
    if (riskFilter === 'CRITICAL_ONLY' && total < 30) return false;
    if (riskFilter === 'HIGH_PLUS' && total < 15) return false;
    if (riskFilter === 'MODERATE_PLUS' && total < 7) return false;
    return true;
  });

  const kpiBlocksEl = document.getElementById('kpi-blocks');
  if (kpiBlocksEl) kpiBlocksEl.textContent = filteredFeatures.length.toLocaleString();

  const geojsonLayer = L.geoJSON({
    type: "FeatureCollection",
    features: filteredFeatures
  }, {
    style: function(feature) {
      const p = feature.properties;
      return {
        color: p.color || '#06b6d4',
        weight: 2.2,             // Distinct, visible block boundary border
        opacity: 0.95,
        fillColor: p.color || '#06b6d4',
        fillOpacity: p.fill_opacity || 0.45,
        dashArray: p.total_incidents >= 30 ? '0' : '3, 3'
      };
    },
    onEachFeature: function(feature, layer) {
      const p = feature.properties;

      // Hover Effect: Lights up the exact block boundary with glowing white border
      layer.on('mouseover', function(e) {
        const target = e.target;
        target.setStyle({
          weight: 4.8,
          color: '#ffffff',
          fillOpacity: 0.80
        });
        target.bringToFront();
        updateInspectorCard(p);
      });

      layer.on('mouseout', function(e) {
        geojsonLayer.resetStyle(e.target);
      });

      // Click to Zoom & Inspect
      layer.on('click', function(e) {
        map.fitBounds(e.target.getBounds(), { maxZoom: 16, padding: [40, 40] });
        updateInspectorCard(p);

        const popupHtml = `
          <div style="font-family: inherit; font-size: 0.8rem; padding: 4px;">
            <div style="font-weight: 800; color: #38bdf8; font-size: 0.9rem; margin-bottom: 4px;">
              Manzana ${p.cve_mza} (AGEB ${p.cve_ageb})
            </div>
            <div style="color: #cbd5e1; margin-bottom: 6px;">
              <strong>CVEGEO:</strong> <code>${p.cvegeo}</code><br>
              <strong>Ubicación:</strong> ${p.calle_1} esquina ${p.calle_2}<br>
              <strong>Colonia:</strong> ${p.colonia}
            </div>
            <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px; color: #f8fafc;">
              <div><strong>Siniestros:</strong> ${p.total_incidents}</div>
              <div><strong>Motos:</strong> ${p.moto_count}</div>
              <div><strong>Peatón:</strong> ${p.peaton_count}</div>
              <div><strong>Con Alcohol:</strong> ${p.alcohol_count}</div>
            </div>
            <div style="margin-top: 8px;">
              <span style="background: ${p.color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;">
                ${p.risk_level}
              </span>
            </div>
          </div>
        `;
        layer.bindPopup(popupHtml).openPopup();
      });
    }
  });

  blocksLayer.addLayer(geojsonLayer);
}

function updateInspectorCard(p) {
  const riskEl = document.getElementById('insp-risk');
  const cveEl = document.getElementById('insp-cvegeo');
  const locEl = document.getElementById('insp-location');
  const totEl = document.getElementById('insp-total');
  const typEl = document.getElementById('insp-type');
  const motEl = document.getElementById('insp-moto');
  const alcEl = document.getElementById('insp-alcohol');

  if (riskEl) {
    riskEl.textContent = p.risk_level;
    riskEl.style.backgroundColor = p.color + '33';
    riskEl.style.color = p.color;
  }
  if (cveEl) cveEl.textContent = p.cvegeo;
  if (locEl) locEl.textContent = `${p.calle_1} x ${p.calle_2}, Col. ${p.colonia}`;
  if (totEl) totEl.textContent = p.total_incidents;
  if (typEl) typEl.textContent = p.predominant_type;
  if (motEl) motEl.textContent = p.moto_count;
  if (alcEl) alcEl.textContent = p.alcohol_count;
}

/**
 * Render Incident Point Markers
 */
function renderMarkersLayer() {
  markersLayer.clearLayers();

  if (typeof INCIDENTS_DATA === 'undefined') return;

  const typeFilterEl = document.getElementById('filter-type');
  const typeFilter = typeFilterEl ? typeFilterEl.value : 'ALL';

  const filteredIncidents = INCIDENTS_DATA.filter(d => {
    if (typeFilter !== 'ALL' && d.type !== typeFilter) return false;
    return true;
  });

  // Render point markers
  filteredIncidents.slice(0, 2000).forEach(d => {
    let color = '#38bdf8';
    if (d.type.includes('motocicleta')) color = '#f43f5e';
    else if (d.type.includes('peatón')) color = '#f59e0b';
    else if (d.type.includes('ciclista')) color = '#10b981';

    const circle = L.circleMarker([d.lat, d.lon], {
      radius: 4.0,
      fillColor: color,
      color: '#ffffff',
      weight: 0.6,
      opacity: 0.9,
      fillOpacity: 0.8
    });

    circle.bindTooltip(`${d.type} (${d.c1} x ${d.c2})`, { direction: 'top', offset: [0, -4] });
    markersLayer.addLayer(circle);
  });
}

function initHeatLayer() {
  if (typeof INCIDENTS_DATA === 'undefined') return;
  const pts = INCIDENTS_DATA.map(d => [d.lat, d.lon, 0.7]);
  heatLayer = L.heatLayer(pts, {
    radius: 18,
    blur: 14,
    maxZoom: 16,
    max: 1.0,
    gradient: {
      0.2: '#06b6d4',
      0.5: '#f59e0b',
      0.8: '#f43f5e',
      1.0: '#ffffff'
    }
  });
}

function updateKpis() {
  if (typeof INCIDENTS_DATA === 'undefined') return;
  const total = INCIDENTS_DATA.length;
  const moto = INCIDENTS_DATA.filter(d => d.type.includes('motocicleta')).length;
  const peaton = INCIDENTS_DATA.filter(d => d.type.includes('peatón')).length;

  const totEl = document.getElementById('kpi-total');
  const motEl = document.getElementById('kpi-moto');
  const peaEl = document.getElementById('kpi-peaton');
  const pctEl = document.getElementById('kpi-moto-pct');

  if (totEl) totEl.textContent = total.toLocaleString();
  if (motEl) motEl.textContent = moto.toLocaleString();
  if (peaEl) peaEl.textContent = peaton.toLocaleString();

  if (pctEl) {
    const motoPct = Math.round((moto / total) * 100);
    pctEl.textContent = `${motoPct}% del total`;
  }
}

// Global Zoom Function
window.zoomTo = function(lon, lat, zoomLevel) {
  if (map) {
    map.flyTo([lat, lon], zoomLevel, {
      duration: 1.2,
      easeLinearity: 0.25
    });
  }
};
