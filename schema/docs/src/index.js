import express from "express";
import cors from "cors";

const app = express();

app.use(cors());
app.use(express.static("./src/public"));

app.listen(3000, () => {
    console.log("Serving docs on port: 3000");
});
