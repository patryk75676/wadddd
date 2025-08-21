const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
app.use(bodyParser.json());

// Twój Discord webhook (wklejony na stałe zgodnie z prośbą)
const DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1408150330511982753/JNw7CFSdqngQiOBVOCh0Bmt2VzJ6bwAocxf5Og-4m29vq-LeqX3mZk73P9fFjXdZvWGJ";

// Strona testowa
app.get("/", (req, res) => {
  res.send("✅ Webhook listener live. POST /webhook aby przesłać dane.");
});

// Odbiór webhooka z MySellAuth
app.post("/webhook", async (req, res) => {
  try {
    const payload = req.body || {};
    const fullJson = JSON.stringify(payload, null, 2);

    // Discord ma limit 2000 znaków w polu content – przytnijmy bezpiecznie do ~1800
    const maxLen = 1800;
    const snippet = fullJson.length > maxLen
      ? fullJson.slice(0, maxLen) + "\n...(truncated)"
      : fullJson;

    const content = "📩 **Nowy webhook z MySellAuth** — pełny JSON poniżej:\n```json\n" + snippet + "\n```";

    await axios.post(DISCORD_WEBHOOK_URL, { content });

    console.log("📦 Webhook payload:", payload);
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error("❌ Błąd przy wysyłce do Discord:", err.message);
    res.status(200).json({ ok: true }); // zwróć 200, żeby MySellAuth nie retriowało w kółko
  }
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
