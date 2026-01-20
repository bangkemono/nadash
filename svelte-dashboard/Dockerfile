# --- Stage 1: Build the App ---
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
# This creates the 'build' folder using adapter-node
RUN npm run build
RUN npm prune --production

# --- Stage 2: Run the App ---
FROM node:20-alpine

WORKDIR /app
# Copy only the built files from Stage 1
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .

# Expose SvelteKit's default port
EXPOSE 3000
# Allow connections from outside
ENV HOST=0.0.0.0
ENV PORT=3000

# Start the server
CMD ["node", "build"]
