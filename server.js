const express = require("express");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const { PDFDocument } = require("pdf-lib");

const app = express();
const upload = multer({ dest: "uploads/" });

app.use(express.static("public")); // index.html 위치

app.post("/merge", upload.array("pdfFiles"), async (req, res) => {
  try {
    const outputFilename = req.body.outputFilename || "합쳐진파일";
    const mergedPdf = await PDFDocument.create();

    for (const file of req.files) {
      const pdfBytes = fs.readFileSync(file.path);
      const pdf = await PDFDocument.load(pdfBytes);
      const copiedPages = await mergedPdf.copyPages(pdf, pdf.getPageIndices());
      copiedPages.forEach((page) => mergedPdf.addPage(page));
    }

    const mergedPdfBytes = await mergedPdf.save();

    const encodedFilename = encodeURIComponent(outputFilename + ".pdf");
    res.setHeader("Content-Disposition", `attachment; filename*=UTF-8''${encodedFilename}`);
    res.setHeader("Content-Type", "application/pdf");

    res.send(Buffer.from(mergedPdfBytes));

    req.files.forEach((file) => fs.unlinkSync(file.path));
  } catch (error) {
    console.error("Error:", error);
    res.status(500).send("PDF 합치기 중 오류 발생");
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`✅ Server running on port ${PORT}`));