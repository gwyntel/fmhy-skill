---
page: "Selfhosting FMHY"
source_title: "Selfhosting"
slug: "other/selfhosting"
source_class: other
source_url: https://fmhy.net/other/selfhosting
upstream_path: docs/other/selfhosting.md
upstream_blob: https://github.com/fmhy/edit/blob/f14105db2c0c0422ec6587d769919164716e45f6/docs/other/selfhosting.md
upstream_commit: f14105db2c0c0422ec6587d769919164716e45f6
captured_at: 2026-09-16T18:15:54Z
link_count: 16
---

# Selfhosting FMHY

# Selfhosting

### Docker (Experimental)

To run a local instance, you will need to install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).
git clone https://github.com/fmhy/edit.git
### Nix Flake

You can use [nix](https://nixos.org/) to set up a development environment, we have a [flake](https://nixos.wiki/wiki/Flakes) that setups `nodejs` and `pnpm`.
1. Fork the repository and clone it to your local machine with `git clone https://github.com/fmhy/edit.git`.
### Manually

- [Git](https://git-scm.com/downloads)
- [Node.js](https://nodejs.org/en/download/) - Install version 25.2.1
- [pnpm 9.12.2+](https://pnpm.io/installation)
#### Step 1: Clone the Repository

git clone https://github.com/fmhy/edit.git
#### Step 2: Install Dependencies

#### Step 3: Development Mode

# Start the documentation site in dev mode

# Start the API in dev mode (if needed)

The development server will start at `http://localhost:5173` by default.
#### Step 4: Building for Production

  - `build`: Build options (can be configured with [Environment Variables](/other/selfhosting#environment-variables))
# Build the documentation site

# Build the API (if needed) using the Node.js preset

#### Step 5: Preview Production Build

# Preview the documentation site

# Preview the API (if needed)

#### Step 6: Deploy

See the [VitePress deployment guide](https://vitepress.dev/guide/deploy) for more info.
### API Deployment

#### Prerequisites

- A [Cloudflare account](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed globally
#### Step 1: Configure Wrangler

#### Step 2: Create KV Namespace

#### Step 3: Build and Deploy

# Build the API

# Deploy to Cloudflare Workers

#### Rate Limiting (Optional)

#### Environment Variables

##### Build-time Variables (for Documentation)

##### Runtime Variables (for API Worker)

#### Troubleshooting

### Reverse Proxy

You should be able to use any reverse proxy with this vitepress website, but find a reasonable config for an nginx server [in the repo here](https://github.com/fmhy/edit/blob/main/.github/assets/nginx.conf)
