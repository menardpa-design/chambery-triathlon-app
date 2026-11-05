// Script des retours de l'appli Chambéry Triathlon.
// Écrit chaque message dans l'onglet « Retours » du Sheet « Plan adulte 2026-2027 ».
var SHEET_ID = '1qHhiG3OtCe5Vy5gAxbrJZCgsrTiBIR3Szcm1gMeVInc';

function onglet_() { return SpreadsheetApp.openById(SHEET_ID).getSheetByName('Retours'); }

// Ouvrir l'URL /exec dans un navigateur : doit afficher « OK, onglet Retours trouvé ».
function doGet() {
  return ContentService.createTextOutput(onglet_() ? 'OK, onglet Retours trouvé' : 'Onglet Retours introuvable');
}

function doPost(e) {
  var d = JSON.parse(e.postData.contents);
  var cut = function (v, n) { return String(v || '').slice(0, n); };
  if (!cut(d.message, 1500) && !cut(d.ressenti, 30)) return ContentService.createTextOutput('vide');
  var lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    onglet_().appendRow([
      new Date(), cut(d.sujet, 60), cut(d.seance, 120), cut(d.ressenti, 30),
      "'" + cut(d.message, 1500), cut(d.nom, 80)
    ]);
  } finally { lock.releaseLock(); }
  return ContentService.createTextOutput('ok');
}
