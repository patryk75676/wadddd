const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");

const app = express();
app.use(bodyParser.json());

// Twój webhook do Discorda
const DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1408150330511982753/JNw7CFSdqngQiOBVOCh0Bmt2VzJ6bwAocxf5Og-4m29vq-LeqX3mZk73P9fFjXdZvWGJ";

app.post("/webhook", async (req, res) => {
  console.log("Webhook received:", req.body);

  try {
    await axios.post(DISCORD_WEBHOOK_URL, {
      content: `📩 Nowe zamówienie!\nTyp: ${req.body.type}\nInvoice ID: ${req.body.data?.invoice_id}`
    });
    console.log("✅ Wysłano na Discorda");
  } catch (error) {
    console.error("❌ Błąd wysyłki na Discord:", error.message);
  }

  res.sendStatus(200);
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Serwer działa na porcie ${PORT}`));
