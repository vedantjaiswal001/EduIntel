# ---- build stage ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
# Use npm install (no lockfile committed) then build the static bundle.
RUN npm install
COPY . .
RUN npm run build

# ---- serve stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
