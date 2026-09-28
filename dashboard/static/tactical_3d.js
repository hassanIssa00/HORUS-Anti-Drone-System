// MCDIS TACTICAL 3D MAP ENGINE (Three.js) — Premium Upgrade
// Renders the Tactical Digital Twin with Terrain and Advanced Target Visualization

let scene, camera, renderer, controls;
let targets = {}; // track_id -> {mesh, rings, trail, data}
let terrain;
const CLOCK = new THREE.Clock();

function initTactical3D() {
    const container = document.getElementById('tactical-3d-container');
    if (!container) return;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x02060b);
    scene.fog = new THREE.FogExp2(0x02060b, 0.0015);

    camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 10000);
    camera.position.set(150, 150, 150);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040, 1.5);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
    directionalLight.position.set(200, 500, 200);
    scene.add(directionalLight);

    // Load Tactical Assets
    createTacticalTerrain();
    createTacticalDigitalTwin();

    // Add Threat Zones
    createThreatZone(0, 0, 80, 0xff0000, "HQ NO-FIRE ZONE");
    
    animate();
}

function createTacticalTerrain() {
    // Generate Tactical Terrain (Dark Wireframe + Solid)
    const size = 2000;
    const segments = 64;
    const geometry = new THREE.PlaneGeometry(size, size, segments, segments);
    
    // Simple noise for terrain
    const vertices = geometry.attributes.position.array;
    for (let i = 0; i < vertices.length; i += 3) {
        const x = vertices[i];
        const y = vertices[i + 1];
        vertices[i + 2] = Math.sin(x / 100) * Math.cos(y / 100) * 15 + (Math.random() * 2);
    }
    geometry.computeVertexNormals();

    const material = new THREE.MeshPhongMaterial({ 
        color: 0x0a1018, 
        wireframe: false,
        shininess: 10,
        flatShading: true
    });
    
    terrain = new THREE.Mesh(geometry, material);
    terrain.rotation.x = -Math.PI / 2;
    terrain.position.y = 0;
    scene.add(terrain);

    // Grid Overlay on Terrain
    const wireframe = new THREE.Mesh(
        geometry,
        new THREE.MeshBasicMaterial({ color: 0x00e5ff, wireframe: true, transparent: true, opacity: 0.05 })
    );
    wireframe.rotation.x = -Math.PI / 2;
    wireframe.position.y = 0.1;
    scene.add(wireframe);
}

function createTacticalDigitalTwin() {
    const buildingMat = new THREE.MeshPhongMaterial({ color: 0x1a2633, transparent: true, opacity: 0.7 });
    const locations = [
        {x: 80, y: 80, w: 25, h: 60, d: 25},
        {x: -120, y: 40, w: 20, h: 30, d: 20},
        {x: 30, y: -100, w: 40, h: 80, d: 40},
        {x: 200, y: 10, w: 15, h: 40, d: 15}
    ];

    locations.forEach(loc => {
        const geo = new THREE.BoxGeometry(loc.w, loc.h, loc.d);
        const mesh = new THREE.Mesh(geo, buildingMat);
        mesh.position.set(loc.x, loc.h/2, loc.y);
        scene.add(mesh);
        
        // Glow effect
        const wire = new THREE.LineSegments(
            new THREE.EdgesGeometry(geo),
            new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.15 })
        );
        wire.position.copy(mesh.position);
        scene.add(wire);
    });
}

function createThreatZone(x, z, radius, color, label) {
    const geo = new THREE.SphereGeometry(radius, 32, 32);
    const mat = new THREE.MeshBasicMaterial({ 
        color: color, 
        transparent: true, 
        opacity: 0.05, 
        side: THREE.DoubleSide 
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x, 0, z);
    scene.add(mesh);

    // Pulsing Edge Ring
    const edge = new THREE.Mesh(
        new THREE.TorusGeometry(radius, 0.8, 16, 100),
        new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.4 })
    );
    edge.position.set(x, 1, z);
    edge.rotation.x = Math.PI / 2;
    scene.add(edge);
    threatZones.push({ mesh: edge, baseScale: 1 });
}

let threatZones = [];

function createUAVMesh(threatLevel) {
    const group = new THREE.Group();
    const color = threatLevel === 'CRITICAL' ? 0xff0000 : 0x00e5ff;
    const material = new THREE.MeshPhongMaterial({ color: color, emissive: color, emissiveIntensity: 0.5 });

    // Center body
    const body = new THREE.Mesh(new THREE.BoxGeometry(2, 0.5, 4), material);
    group.add(body);

    // Wings
    const wings = new THREE.Mesh(new THREE.BoxGeometry(8, 0.2, 1.5), material);
    group.add(wings);

    // Rotors (symbolic)
    [[-3.5, 1], [3.5, 1], [-3.5, -1], [3.5, -1]].forEach(pos => {
        const rotor = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 0.1, 8), material);
        rotor.position.set(pos[0], 0.3, pos[1]);
        group.add(rotor);
    });

    return group;
}

function updateTarget(id, x, y, z, threatLevel) {
    if (!targets[id]) {
        const uav = createUAVMesh(threatLevel);
        scene.add(uav);

        // Ground Ring
        const ringGeo = new THREE.TorusGeometry(5, 0.2, 16, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.5 });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        scene.add(ring);

        // Vertical Indicator Line
        const lineMat = new THREE.LineDashedMaterial({ color: 0x00e5ff, dashSize: 2, gapSize: 2 });
        const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,100,0)]);
        const line = new THREE.Line(lineGeo, lineMat);
        line.computeLineDistances();
        scene.add(line);

        targets[id] = { mesh: uav, ring: ring, line: line, trail: [] };
    }
    
    // Update position (Coordinate mapping: Dashboard X/Y -> ThreeJS X/Z)
    // Elevation (Z in dashboard) -> ThreeJS Y
    const targetY = z || 20; 
    targets[id].mesh.position.set(x, targetY, y);
    targets[id].ring.position.set(x, 0.5, y);
    
    // Update line
    targets[id].line.position.set(x, 0, y);
    targets[id].line.scale.y = targetY / 100;

    // Rotation based on movement (simple look-ahead could be added)
    targets[id].mesh.rotation.y += 0.02;
}

function animate() {
    requestAnimationFrame(animate);
    const time = CLOCK.getElapsedTime();

    // Pulse threat zones
    threatZones.forEach(zone => {
        const s = 1 + Math.sin(time * 2) * 0.05;
        zone.mesh.scale.set(s, s, 1);
        zone.mesh.material.opacity = 0.3 + Math.sin(time * 2) * 0.1;
    });

    // Animate target rings and markers
    Object.values(targets).forEach(t => {
        t.ring.scale.set(1 + Math.sin(time * 4) * 0.2, 1 + Math.sin(time * 4) * 0.2, 1);
        t.ring.material.opacity = 0.5 + Math.sin(time * 4) * 0.2;
    });

    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    const container = document.getElementById('tactical-3d-container');
    if (!container || !camera) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});
