# Frontend

This directory houses the Next.js 15 application that powers the French Novel Tool interface.

## Requirements

- Node.js 18 or newer
- npm 9+ (or your preferred Node package manager)

## Environment variables

Copy the example file and adjust it with your own values:

```
cp .env.example .env.local
```

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the Flask backend (defaults to `http://localhost:5000`). |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Google OAuth client ID used for Drive picker authentication. |
| `NEXT_PUBLIC_GOOGLE_API_KEY` | Google API key that enables Drive APIs. |

## Install dependencies

```
npm install
```

## Run the development server

```
npm run dev
```

The app is served at [http://localhost:3000](http://localhost:3000).

## Additional scripts

- `npm run build` – create a production build
- `npm run start` – serve the production build
- `npm run lint` – lint the project

For a complete setup walkthrough (backend + frontend), refer to the root `README.md`.
