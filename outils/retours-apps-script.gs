// À coller dans le Sheet « Plan adulte 2026-2027 » : Extensions > Apps Script.
// Reçoit les messages de l'onglet Retours de l'appli et les ajoute dans l'onglet « Retours ».
function doPost(e) {
  var d = JSON.parse(e.postData.contents);
  var cut = function (v, n) { return String(v || '').slice(0, n); };
  if (!cut(d.message, 1500) && !cut(d.ressenti, 30)) return ContentService.createTextOutput('vide');
  var lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    SpreadsheetApp.getActive().getSheetByName('Retours').appendRow([
      new Date(), cut(d.sujet, 60), cut(d.seance, 120), cut(d.ressenti, 30),
      "'" + cut(d.message, 1500), cut(d.nom, 80)
    ]);
  } finally { lock.releaseLock(); }
  return ContentService.createTextOutput('ok');
}
