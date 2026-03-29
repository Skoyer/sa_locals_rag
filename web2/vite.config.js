import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const wordcloudsDir = path.resolve(__dirname, '../wordclouds');

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'serve-wordclouds',
      configureServer(server) {
        server.middlewares.use('/wordclouds', (req, res, next) => {
          const raw = req.url?.split('?')[0] || '/';
          const rel = path.normalize(decodeURIComponent(raw)).replace(/^[/\\]+/, '');
          if (rel.includes('..')) {
            res.statusCode = 403;
            return res.end();
          }
          const filePath = path.join(wordcloudsDir, rel);
          if (!filePath.startsWith(wordcloudsDir)) {
            res.statusCode = 403;
            return res.end();
          }
          fs.stat(filePath, (err, st) => {
            if (err || !st.isFile()) return next();
            const ext = path.extname(filePath).toLowerCase();
            const mime =
              ext === '.png'
                ? 'image/png'
                : ext === '.jpg' || ext === '.jpeg'
                  ? 'image/jpeg'
                  : 'application/octet-stream';
            res.setHeader('Content-Type', mime);
            fs.createReadStream(filePath).pipe(res);
          });
        });
      },
    },
    {
      name: 'copy-wordclouds-dist',
      closeBundle() {
        if (!fs.existsSync(wordcloudsDir)) return;
        const out = path.join(__dirname, 'dist', 'wordclouds');
        fs.cpSync(wordcloudsDir, out, { recursive: true });
      },
    },
  ],
});
