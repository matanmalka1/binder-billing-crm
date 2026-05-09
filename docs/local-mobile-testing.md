# Local Mobile Testing

Use this when testing the Vite frontend from a phone on the same Wi-Fi as the laptop.

1. Get the Mac LAN IP:

   ```bash
   ipconfig getifaddr en0
   ```

   If Wi-Fi is not on `en0`, run:

   ```bash
   networksetup -listallhardwareports
   ```

   Then use the matching device name with `ipconfig getifaddr <device>`.

2. In `../frontend/.env.local`, set:

   ```bash
   VITE_API_BASE_URL=http://<LAN_IP>:8000/api/v1
   ```

   Do not commit `.env.local`; it is ignored by the frontend `.gitignore`.

3. In the backend environment used locally, include both laptop and phone-facing frontend origins:

   ```bash
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://<LAN_IP>:5173
   ```

   Keep production CORS explicit. Do not use `*` with credentials.

4. Run the backend from this repo:

   ```bash
   APP_ENV=development ENV_FILE=.env.development python -m app.main
   ```

   `app.main` binds to `0.0.0.0` on port `8000` in development.

5. Run the frontend from `../frontend`:

   ```bash
   npm run dev:lan
   ```

   Equivalent:

   ```bash
   npm run dev -- --host 0.0.0.0
   ```

6. Open this URL from the phone:

   ```text
   http://<LAN_IP>:5173
   ```
