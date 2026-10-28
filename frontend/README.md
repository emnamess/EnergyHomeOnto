# Frontend

Application hôte React + TypeScript + Vite. Lancer avec `npm install` puis
`npm run dev`. Les cinq parcours individuels sont dans `src/features/` ; le module
de recherche partagé est dans `src/shared/recherche-intelligente/`. Le proxy Vite
transmet `/api` à FastAPI sur le port 8000.

Pour ajouter une page : la déclarer dans `ROUTES` (`src/shared/AppNav.tsx`) et dans
`src/App.tsx`. Voir le guide pas à pas dans le `README.md` racine (§ 6).
