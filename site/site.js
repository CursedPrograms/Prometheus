// Prometheus' page: the feature cards and the year
(function () {
  'use strict';
  const features = [
    ['People from sliders', 'MB-Lab: realistic men and women from body, face, age, mass and tone sliders, measurements, expressions, a face rig and skin and eye materials.'],
    ['CharMorph', 'Faster morphing on four bases (MB-Lab female and male, Antonia, Reom), skin and eye colours, hairstyles, clothes that fit as you shape, and a Rigify rig with a full face rig.'],
    ['SMPL-X bodies', 'The body model of AI and motion capture research: shape and expression sliders, a skeleton fitted to the shape, random bodies. Bring your own model files.'],
    ['Live motion capture', 'The Pantomimus tab drives an armature from your webcam as you move, through Pantomimus, and records it as keyframes.'],
    ['Everything in a 3D suite', 'Modelling, sculpting, UV and texture painting, rigging, animation, simulation, Cycles and EEVEE rendering, compositing and video editing.'],
    ['The Atelier look', 'The Atelier blue, square corners, no shadows, and its own settings folder: it never touches a Blender install. Files and add-ons for Blender 5.4 work as they are.']
  ];
  const grid = document.getElementById('features');
  if (grid) {
    for (const [title, text] of features) {
      const card = document.createElement('article');
      const h = document.createElement('h2');
      h.textContent = title;
      const p = document.createElement('p');
      p.textContent = text;
      card.append(h, p);
      grid.appendChild(card);
    }
  }
  const year = document.getElementById('year');
  if (year) year.textContent = String(Math.max(2026, new Date().getFullYear()));
})();
