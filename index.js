const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = process.env.PORT || 10000;

app.use(bodyParser.json());

// Prosty webhook
app.post("/webhook", (req, res) => {
  console.log("📩 Webhook received:", req.body);
  res.status(200).send("Webhook OK");
});

// Test GET
app.get("/", (req, res) => {
  res.send("✅ Serwer działa");
});

app.listen(PORT, () => {
  console.log(`🚀 Serwer działa na porcie ${PORT}`);
});
