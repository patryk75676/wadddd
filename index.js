const express = require("express");
const app = express();
const PORT = process.env.PORT || 3000;

app.get("/", (req, res) => {
  res.send("✅ Działa! Twoja aplikacja jest online 🚀");
});

// opcjonalny ping do budzenia przez UptimeRobot
app.get("/ping", (req, res) => res.status(200).send("pong"));

app.listen(PORT, () => {
  console.log(`Serwer działa na porcie ${PORT}`);
});
