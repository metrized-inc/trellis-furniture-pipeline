document.getElementById('mesh-form').addEventListener('submit', function() {
    console.log('Mesh form submitted');
    document.getElementById('loading-mesh').classList.remove('hidden');
});
  
document.getElementById('retex-form').addEventListener('submit', function() {
    document.getElementById('loading-retex').classList.remove('hidden');
});

window.addEventListener("focus", function () {
    // Hide all loading indicators when the window regains focus
    const loadingMesh = document.getElementById("loading-mesh");
    const loadingRetex = document.getElementById("loading-retex");
    if (loadingMesh && !loadingMesh.classList.contains("hidden")) {
        loadingMesh.classList.add("hidden");
    }
    if (loadingRetex && !loadingRetex.classList.contains("hidden")) {
        loadingRetex.classList.add("hidden");
    }
});

// wrap everything that touches the DOM in DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {

  /* existing form-submit handlers ... */

  // GLB button
  const glbBtn = document.getElementById('submit-glb');
  if (glbBtn) {
    console.log('#submit-glb found, binding event listener');
    glbBtn.addEventListener('click', () => {
      console.log('Submitting to GLB via event listener');
      const form = document.getElementById('mesh-form');

      // change action, show spinner, then submit
      form.action = '/trellis-glb';
      document.getElementById('loading-mesh').classList.remove('hidden');
      form.submit();
    });
  } else {
    console.warn('#submit-glb not found when binding listener');
  }
});