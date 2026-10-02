import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({
  server:{port:5173,fs:{allow:[fileURLToPath(new URL('../../../',import.meta.url))]},proxy:{'/api':'http://127.0.0.1:5000','/health':'http://127.0.0.1:5000'}},
});
