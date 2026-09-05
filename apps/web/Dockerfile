FROM node:22-slim AS base
WORKDIR /app
RUN corepack enable

FROM base AS deps
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./
# Baked into the client bundle at build time -- must be the URL the
# *browser* reaches the API at, not the in-network "backend" service name
# used by server-to-server calls.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN pnpm build

FROM base AS runner
ENV NODE_ENV=production
RUN groupadd -r nextjs && useradd -r -g nextjs nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
