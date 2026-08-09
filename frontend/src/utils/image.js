// Ridimensiona un'immagine lato client prima di convertirla in data URL:
// una foto profilo (o un logo aziendale) non ha bisogno di essere a piena
// risoluzione, e mandarla intera gonfierebbe inutilmente il documento
// MongoDB (vedi PHOTO_MAX_LENGTH in core/validation_limits.py, pensato per
// una miniatura compressa, non per un file originale da smartphone).
export function resizeImageToDataUrl(file, maxDim = 300) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = reject;
    reader.onload = () => {
      const img = new Image();
      img.onerror = reject;
      img.onload = () => {
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.8));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}
