# =========================================================
# Frontend Dockerfile — React + Vite (multi-stage build)
# =========================================================

# ---------- Stage 1: build the React app ----------
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# ---------- Stage 2: serve with Nginx ----------
FROM nginx:alpine

# Replace the default Nginx site with our own config
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built app from Stage 1 — the final image never contains
# node_modules or the source code, only the compiled static files.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
