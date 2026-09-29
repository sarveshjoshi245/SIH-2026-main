# AGENTS.md

## Status

Project initialized on branch `sarv` with Government Interoperability Platform backend & native e-KYC frontend.

## Project Structure & Entrypoints

- **Backend / Static Server**: `server/src/server.js` (Express on port `5000`)
- **Native Frontend Static Files**: `server/public/` (`index.html`, `css/gov-style.css`, `js/app.js`)
- **Land Records Mock API**: `server/src/routes/landRoutes.js`
- **Auth & e-KYC Routes**: `server/src/routes/authRoutes.js`
- **Interoperability Engine**: `server/src/routes/interopRoutes.js`

## Commands

- **Install Dependencies**:
  ```bash
  cd server && npm install
  ```
- **Start Server**:
  ```bash
  cd server && npm start
  ```
  Access website at `http://localhost:5000`.

## Git Branches

- Active development branch: `sarv`
