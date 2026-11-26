(function () {
  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  function makeLabel(text, color) {
    var canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 128;
    var context = canvas.getContext("2d");
    context.fillStyle = "rgba(5,7,13,0.72)";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.font = "600 42px Segoe UI, Arial";
    context.fillStyle = color;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    var texture = new THREE.CanvasTexture(canvas);
    var sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }));
    sprite.scale.set(38, 9.5, 1);
    return sprite;
  }

  ready(function () {
    var container = document.getElementById("network-scene");
    var dataElement = document.getElementById("graph-data");
    if (!container || !dataElement || !window.THREE) {
      if (container) { container.textContent = "3D network requires the Three.js library."; }
      return;
    }

    var payload = JSON.parse(dataElement.textContent || "{}");
    var nodes = payload.nodes || [];
    var edges = payload.edges || [];
    if (!nodes.length) {
      container.textContent = "No network nodes available. Seed the synthetic demo data to generate a graph.";
      return;
    }

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 5000);
    camera.position.set(0, 0, 420);
    var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.65));
    var keyLight = new THREE.PointLight(0xd4af37, 1.4, 1800);
    keyLight.position.set(240, 260, 420);
    scene.add(keyLight);
    var fillLight = new THREE.PointLight(0x5b8bd0, 1.0, 1800);
    fillLight.position.set(-320, -180, 260);
    scene.add(fillLight);

    var controls = null;
    if (THREE.OrbitControls) {
      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.35;
    }

    var group = new THREE.Group();
    scene.add(group);
    var positions = {};
    var maxAbs = 1;
    nodes.forEach(function (node) {
      var position = node.position || { x: 0, y: 0, z: 0 };
      maxAbs = Math.max(maxAbs, Math.abs(position.x || 0), Math.abs(position.y || 0));
    });
    var scale = 150 / maxAbs;
    nodes.forEach(function (node) {
      var source = node.position || { x: 0, y: 0, z: 0 };
      var position = new THREE.Vector3((source.x || 0) * scale, (source.y || 0) * scale, (source.z || 0) * 18);
      positions[node.id] = position;
      var color = node.kind === "account" ? 0xd4af37 : node.kind === "cluster" ? 0xff5f6d : 0xb8c4d4;
      var radius = node.kind === "account" ? 8 : node.kind === "cluster" ? 7 : 5;
      if (node.risk >= 75) { radius += 2; }
      var mesh = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 24, 24),
        new THREE.MeshStandardMaterial({ color: color, emissive: color, emissiveIntensity: node.risk >= 75 ? 0.55 : 0.2, roughness: 0.32, metalness: 0.72 })
      );
      mesh.position.copy(position);
      group.add(mesh);
      var label = makeLabel(node.label || node.id, node.kind === "account" ? "#f1d17a" : "#b8c4d4");
      label.position.copy(position).add(new THREE.Vector3(0, radius + 14, 0));
      group.add(label);
    });

    edges.forEach(function (edge) {
      var source = positions[edge.source];
      var target = positions[edge.target];
      if (!source || !target) { return; }
      var geometry = new THREE.BufferGeometry().setFromPoints([source, target]);
      var strength = Math.min(1, Math.max(0.12, (edge.count || 1) / 12));
      var material = new THREE.LineBasicMaterial({ color: 0x9fb7d4, transparent: true, opacity: 0.18 + strength * 0.45 });
      group.add(new THREE.Line(geometry, material));
    });

    var animationFrame = function () {
      requestAnimationFrame(animationFrame);
      if (controls) { controls.update(); }
      group.rotation.y += 0.0007;
      renderer.render(scene, camera);
    };
    animationFrame();

    window.addEventListener("resize", function () {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    });
  });
})();
