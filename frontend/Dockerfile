# Frontend Next.js — pensado para Coolify (Base Directory: /frontend).
#
# OJO con NEXT_PUBLIC_API_URL: es una variable "de build", no de runtime —
# Next.js la hornea dentro del JS que corre en el navegador durante `npm
# run build`, así que hay que pasarla como Build Argument en Coolify (no
# solo como variable de entorno normal del contenedor), con la URL pública
# del backend (ej. https://api.sst-cctv.com). Si se cambia después de
# construida la imagen, hay que reconstruir — no basta con reiniciar.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
