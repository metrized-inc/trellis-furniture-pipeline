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