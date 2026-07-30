(function () {
  "use strict";
  var canvas = document.querySelector(".login-wave-canvas");
  if (!canvas || !canvas.getContext) return;
  var context = canvas.getContext("2d");
  if (!context) return;
  var reducedMotion = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  var embedded = (" " + document.documentElement.className + " ").indexOf(" embedded-1c ") !== -1;
  var columns = 96;
  var rows = 32;
  var frameInterval = 1000 / (embedded ? 30 : 24);
  var width = 0, height = 0, pixelRatio = 1, lastFrame = 0, animationFrame = 0, resizeTimer = 0, phase = 0;
  var horizonGlow = null;
  var pointCount = columns * rows;
  var NumberArray = window.Float32Array || Array;
  var gridX = new NumberArray(pointCount);
  var gridY = new NumberArray(pointCount);
  var depthValues = new NumberArray(rows);
  var horizontalValues = new NumberArray(columns);
  var amplitudeValues = new NumberArray(rows);
  var spreadValues = new NumberArray(rows);
  var baseYValues = new NumberArray(rows);
  var lineColor = embedded ? "255, 190, 50" : "231, 183, 54";
  var pointColor = embedded ? "255, 205, 64" : "255, 215, 67";
  var brightness = embedded ? 1.48 : 1;
  var dayTheme = false;
  var requestFrame = window.requestAnimationFrame || function (callback) {
    return window.setTimeout(function () { callback(new Date().getTime()); }, frameInterval);
  };
  var cancelFrame = window.cancelAnimationFrame || window.clearTimeout;

  function applyPalette() {
    dayTheme = document.documentElement.getAttribute("data-theme") === "day";
    if (dayTheme) {
      lineColor = embedded ? "142, 96, 24" : "157, 111, 34";
      pointColor = embedded ? "129, 84, 15" : "141, 94, 20";
      brightness = embedded ? 1.05 : 0.88;
    } else {
      lineColor = embedded ? "255, 190, 50" : "231, 183, 54";
      pointColor = embedded ? "255, 205, 64" : "255, 215, 67";
      brightness = embedded ? 1.48 : 1;
    }
  }

  function resize() {
    width = Math.max(320, window.innerWidth || document.documentElement.clientWidth);
    height = Math.max(320, window.innerHeight || document.documentElement.clientHeight);
    pixelRatio = Math.min(window.devicePixelRatio || 1, embedded ? 1 : 1.25);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    for (var row = 0; row < rows; row += 1) {
      amplitudeValues[row] = height * (0.008 + depthValues[row] * 0.038);
      spreadValues[row] = width * (0.54 + depthValues[row] * 0.13);
      baseYValues[row] = height * 0.565 + Math.pow(depthValues[row], 1.58) * height * 0.465;
    }
    horizonGlow = context.createLinearGradient(0, height * 0.47, 0, height * 0.72);
    if (dayTheme) {
      horizonGlow.addColorStop(0, "rgba(150, 102, 25, 0)");
      horizonGlow.addColorStop(0.42, "rgba(150, 102, 25, .025)");
      horizonGlow.addColorStop(0.68, "rgba(150, 102, 25, .085)");
      horizonGlow.addColorStop(1, "rgba(150, 102, 25, 0)");
    } else {
      horizonGlow.addColorStop(0, embedded ? "rgba(255, 76, 0, 0)" : "rgba(255, 190, 24, 0)");
      horizonGlow.addColorStop(0.42, embedded ? "rgba(255, 76, 0, .08)" : "rgba(255, 178, 13, .035)");
      horizonGlow.addColorStop(0.68, embedded ? "rgba(255, 104, 0, .20)" : "rgba(255, 198, 35, .12)");
      horizonGlow.addColorStop(1, embedded ? "rgba(255, 76, 0, 0)" : "rgba(255, 174, 8, 0)");
    }
  }

  function calculateRow(row, time) {
    var column, index = row * columns;
    var depth = depthValues[row];
    var step = 2 / (columns - 1);
    var angle1 = -4.1 + time * 0.46 + depth * 2.3;
    var angle2 = -8.6 - time * 0.31 + depth * 5.8;
    var angle3 = -2.2 + depth * 9.4 - time * 0.38;
    var sin1 = Math.sin(angle1), cos1 = Math.cos(angle1);
    var sin2 = Math.sin(angle2), cos2 = Math.cos(angle2);
    var sin3 = Math.sin(angle3), cos3 = Math.cos(angle3);
    var sinStep1 = Math.sin(step * 4.1), cosStep1 = Math.cos(step * 4.1);
    var sinStep2 = Math.sin(step * 8.6), cosStep2 = Math.cos(step * 8.6);
    var sinStep3 = Math.sin(step * 2.2), cosStep3 = Math.cos(step * 2.2);
    var nextSin, nextCos, wave;
    for (column = 0; column < columns; column += 1) {
      wave = sin1 * 0.5 + sin2 * 0.28 + cos3 * 0.22;
      gridX[index] = width * 0.5 + horizontalValues[column] * spreadValues[row];
      gridY[index] = baseYValues[row] + wave * amplitudeValues[row];
      index += 1;
      nextSin = sin1 * cosStep1 + cos1 * sinStep1;
      nextCos = cos1 * cosStep1 - sin1 * sinStep1;
      sin1 = nextSin; cos1 = nextCos;
      nextSin = sin2 * cosStep2 + cos2 * sinStep2;
      nextCos = cos2 * cosStep2 - sin2 * sinStep2;
      sin2 = nextSin; cos2 = nextCos;
      nextSin = sin3 * cosStep3 + cos3 * sinStep3;
      nextCos = cos3 * cosStep3 - sin3 * sinStep3;
      sin3 = nextSin; cos3 = nextCos;
    }
  }

  function drawRow(row, alpha, lineWidth) {
    var column, index = row * columns;
    context.beginPath();
    context.moveTo(gridX[index], gridY[index]);
    for (column = 1; column < columns; column += 1) {
      index += 1;
      context.lineTo(gridX[index], gridY[index]);
    }
    context.strokeStyle = "rgba(" + lineColor + ", " + Math.min(1, alpha * brightness) + ")";
    context.lineWidth = lineWidth;
    context.stroke();
  }

  function drawColumn(column, alpha, lineWidth) {
    var row, index = column;
    context.beginPath();
    context.moveTo(gridX[index], gridY[index]);
    for (row = 1; row < rows; row += 1) {
      index += columns;
      context.lineTo(gridX[index], gridY[index]);
    }
    context.strokeStyle = "rgba(" + lineColor + ", " + Math.min(1, alpha * brightness) + ")";
    context.lineWidth = lineWidth;
    context.stroke();
  }

  function render(time) {
    var row, column, depth, radius, index;
    context.clearRect(0, 0, width, height);
    context.globalCompositeOperation = embedded ? "source-over" : "lighter";
    if (!embedded) {
      context.fillStyle = horizonGlow;
      context.fillRect(0, height * 0.45, width, height * 0.3);
    }
    for (row = 0; row < rows; row += 1) {
      calculateRow(row, time);
    }
    for (row = 0; row < rows; row += 1) {
      depth = depthValues[row];
      drawRow(row, 0.035 + depth * 0.17, 0.42 + depth * 0.32);
    }
    for (column = 0; column < columns; column += 2) {
      drawColumn(column, 0.045, 0.38);
    }
    for (row = 0; row < rows; row += 1) {
      depth = depthValues[row];
      context.fillStyle = "rgba(" + pointColor + ", " + Math.min(1, (0.26 + depth * 0.54) * brightness) + ")";
      radius = 0.48 + depth * 0.82;
      if (embedded) {
        for (column = 0; column < columns; column += 1) {
          index = row * columns + column;
          context.fillRect(gridX[index] - radius, gridY[index] - radius, radius * 2, radius * 2);
        }
      } else {
        context.beginPath();
        for (column = 0; column < columns; column += 1) {
          index = row * columns + column;
          context.moveTo(gridX[index] + radius, gridY[index]);
          context.arc(gridX[index], gridY[index], radius, 0, Math.PI * 2);
        }
        context.fill();
      }
    }
    context.globalCompositeOperation = "source-over";
  }

  function tick(timestamp) {
    var elapsed = timestamp - lastFrame;
    if (elapsed >= frameInterval - 1) {
      lastFrame = timestamp - (elapsed % frameInterval);
      if (embedded) {
        phase += frameInterval * 0.001;
        render(phase);
      } else {
        render(timestamp * 0.001);
      }
    }
    animationFrame = requestFrame(tick);
  }
  function start() {
    cancelFrame(animationFrame);
    if (reducedMotion.matches) render(0);
    else animationFrame = requestFrame(tick);
  }
  function scheduleResize() {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      resize();
      if (reducedMotion.matches) render(0);
    }, 120);
  }
  window.addEventListener("resize", scheduleResize, false);
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) cancelFrame(animationFrame);
    else start();
  }, false);
  if (reducedMotion.addListener) reducedMotion.addListener(start);
  window.addEventListener("supportbot-theme-change", function () {
    applyPalette();
    resize();
    if (reducedMotion.matches) render(0);
  }, false);
  for (var rowIndex = 0; rowIndex < rows; rowIndex += 1) depthValues[rowIndex] = rowIndex / (rows - 1);
  for (var columnIndex = 0; columnIndex < columns; columnIndex += 1) horizontalValues[columnIndex] = columnIndex / (columns - 1) * 2 - 1;
  applyPalette();
  resize();
  start();
}());
